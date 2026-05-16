"""handlers/ai_handler.py — AI assistant via Anthropic or OpenAI."""
import logging
import aiohttp
from telegram import Update
from telegram.ext import CallbackContext
from config import AI_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


async def ai_command(update: Update, context: CallbackContext) -> None:
    """Ask an AI a question. Usage: /ai <question>"""
    if not context.args:
        await update.message.reply_text("Usage: `/ai <your question>`", parse_mode="Markdown")
        return

    question = " ".join(context.args)
    msg = await update.message.reply_text("🤖 Thinking...")

    try:
        if AI_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
            answer = await _ask_anthropic(question)
        elif OPENAI_API_KEY:
            answer = await _ask_openai(question)
        else:
            answer = (
                "⚠️ No AI API key configured.\n"
                "Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your `.env` file."
            )
        if len(answer) > 3800:
            answer = answer[:3800] + "\n\n_[truncated]_"
        await msg.edit_text(f"🤖 *AI Response*\n\n{answer}", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ AI request failed: `{e}`", parse_mode="Markdown")


async def _ask_anthropic(question: str) -> str:
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": question}],
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
       
        if resp.status != 200:
            error = await resp.text()
            raise RuntimeError(f"Anthropic API error {resp.status}: {error[:200]}")
        data = await resp.json()
        return data["content"][0]["text"]


async def _ask_openai(question: str) -> str:
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": question}],
                "max_tokens": 1024,
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        # BUG FIX: same HTTP status check for OpenAI
        if resp.status != 200:
            error = await resp.text()
            raise RuntimeError(f"OpenAI API error {resp.status}: {error[:200]}")
        data = await resp.json()
        return data["choices"][0]["message"]["content"]
