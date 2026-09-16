"""ai/agent.py — the intelligent router: one Claude call per user message,
which either replies directly (normal chat) or picks a tool to run (mapped
to an existing bot command or a skills/ plugin).

Cost-minimization choices (see README / conversation for the why):
  * Claude Haiku (cheapest current model) by default, configurable.
  * System prompt + full tool catalogue are marked for prompt caching, so
    they're billed at the full rate only once every few minutes; every
    later message in that window pays the much cheaper cached-read price.
  * Only ONE Claude call per user message, ever. When a tool is picked,
    its result is not sent back to Claude for a "nicer" summary — "action"
    tools already reply to the user themselves, and "data" tools just have
    their return value forwarded. No second round-trip, no extra tokens.
  * Short rolling per-chat history (a handful of turns) so the bot still
    feels conversational without re-sending a growing transcript forever.
"""
import logging
import shlex
from collections import defaultdict

import aiohttp
from telegram import Update
from telegram.ext import CallbackContext

from ai import registry
from config import AI_MAX_TOKENS, AI_MODEL, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = (
    "You are the assistant embedded in a private Raspberry Pi control bot on Telegram. "
    "The person messaging you is already an authorized administrator of this Pi. "
    "Use the available tools whenever a request is about the Pi itself (status, network, "
    "files, GPIO, processes, services, and so on). Call at most one tool per reply. "
    "Tools that map to bot commands reply to the user themselves — you don't need to "
    "restate their result, a short one-sentence intro is enough, or none at all. "
    "If no tool is needed, just answer briefly and helpfully, in the same language the "
    "user wrote in. Never invent system data or command output."
)

_HISTORY_MAX_TURNS = 6  # user+assistant pairs kept per chat
_history: dict[int, list[dict]] = defaultdict(list)


def _trim(history: list[dict]) -> None:
    # Drop oldest pairs only, so the transcript always still starts with the
    # required "user" role — Anthropic rejects a messages list that doesn't.
    max_len = _HISTORY_MAX_TURNS * 2
    while len(history) > max_len:
        del history[0]


async def handle_message(update: Update, context: CallbackContext, user_text: str) -> None:
    if not user_text or not user_text.strip():
        return

    if not ANTHROPIC_API_KEY:
        await update.message.reply_text(
            "⚠️ No AI API key configured.\nSet `ANTHROPIC_API_KEY` in your `.env` file.",
            parse_mode="Markdown",
        )
        return

    chat_id = update.effective_chat.id
    history = _history[chat_id]

    try:
        content = await _call_claude(history, user_text)
    except Exception as e:
        logger.error("Claude request failed: %s", e)
        await update.message.reply_text(f"❌ AI request failed: `{e}`", parse_mode="Markdown")
        return

    text_parts = [b["text"] for b in content if b.get("type") == "text" and b.get("text")]
    tool_use = next((b for b in content if b.get("type") == "tool_use"), None)
    lead_text = "\n".join(p.strip() for p in text_parts if p.strip()).strip()

    history.append({"role": "user", "content": user_text})

    if lead_text:
        await update.message.reply_text(lead_text)

    if tool_use is None:
        if not lead_text:
            lead_text = "…"
            await update.message.reply_text("🤖 …")
        history.append({"role": "assistant", "content": lead_text})
        _trim(history)
        return

    await _run_tool(update, context, tool_use)
    # Keep strict user/assistant alternation for the next call, even though
    # the tool replied on Telegram directly rather than through Claude text.
    history.append({
        "role": "assistant",
        "content": lead_text or f"(ran tool: {tool_use.get('name')})",
    })
    _trim(history)


async def _run_tool(update: Update, context: CallbackContext, tool_use: dict) -> None:
    name = tool_use.get("name", "")
    args_str = (tool_use.get("input") or {}).get("args", "") or ""
    tool = registry.get_tool(name)

    if tool is None:
        await update.message.reply_text(f"⚠️ AI tried to use an unknown tool: `{name}`", parse_mode="Markdown")
        return

    try:
        if tool.kind == "action":
            context.args = shlex.split(args_str) if args_str else []
            await tool.handler(update, context)
        else:
            result = await tool.handler(update, context, {"args": args_str})
            if result:
                await update.message.reply_text(str(result)[:3800])
    except Exception as e:
        logger.error("Tool %r failed: %s", name, e, exc_info=True)
        await update.message.reply_text(f"❌ `{name}` failed: `{e}`", parse_mode="Markdown")


async def _call_claude(history: list[dict], user_text: str) -> list[dict]:
    messages = list(history) + [{"role": "user", "content": user_text}]

    body = {
        "model": AI_MODEL,
        "max_tokens": AI_MAX_TOKENS,
        "system": [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
    }
    tool_defs = registry.get_tool_defs()
    if tool_defs:
        body["tools"] = tool_defs
        body["tool_choice"] = {"type": "auto"}

    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            _API_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=aiohttp.ClientTimeout(total=30),
        )
        if resp.status != 200:
            error = await resp.text()
            raise RuntimeError(f"Anthropic API error {resp.status}: {error[:200]}")
        data = await resp.json()
        return data["content"]
