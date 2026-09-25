"""handlers/ai_handler.py — AI entry points: the explicit /ai command and
the smart chat router that lets Claude pick a bot command on its own."""
import logging
import aiohttp
from telegram import Update
from telegram.ext import CallbackContext
from config import AI_SMART_CHAT, ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


async def ai_command(update: Update, context: CallbackContext) -> None:
    """Ask an AI a question. Usage: /ai <question>"""
    if not context.args:
        await update.message.reply_text("Usage: `/ai <your question>`", parse_mode="Markdown")
        return

    question = " ".join(context.args)

    if ANTHROPIC_API_KEY:
        from ai.agent import handle_message
        await handle_message(update, context, question)
        return

    msg = await update.message.reply_text("🤖 Thinking...")
    try:
        if OPENAI_API_KEY:
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


async def ai_chat_handler(update: Update, context: CallbackContext) -> None:
    """Routes plain chat messages (no leading /) through the Claude agent,
    which decides whether to just reply or run one of the bot's commands."""
    if not AI_SMART_CHAT or not ANTHROPIC_API_KEY:
        return
    if not update.message or not update.message.text:
        return

    from ai.agent import handle_message
    await handle_message(update, context, update.message.text)


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

        if resp.status != 200:
            error = await resp.text()
            raise RuntimeError(f"OpenAI API error {resp.status}: {error[:200]}")
        data = await resp.json()
        return data["choices"][0]["message"]["content"]
