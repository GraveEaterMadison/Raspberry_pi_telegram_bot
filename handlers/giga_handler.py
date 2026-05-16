"""handlers/giga_handler.py — GigaChat API connectivity check.

Authenticates with Sberbank's GigaChat OAuth endpoint, then lists available
models. Uses aiohttp instead of the blocking `requests` library so the bot
event loop is never blocked.

Requires in .env:
  GIGACHAT_CREDENTIALS=<base64-encoded credential string>
"""

import logging
import os
import uuid

import aiohttp
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

_OAUTH_URL  = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_MODELS_URL = "https://gigachat.devices.sberbank.ru/api/v1/models"
_CA_BUNDLE  = "/etc/ssl/certs/ca-certificates.crt"


async def giga_check_command(update: Update, context: CallbackContext) -> None:
    """Check GigaChat API reachability and list available models."""
    creds = os.getenv("GIGACHAT_CREDENTIALS", "")
    if not creds:
        await update.message.reply_text(
            "❌ `GIGACHAT_CREDENTIALS` not set in `.env`.\n"
            "Get credentials from developers.sber.ru/gigachat.",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text("🤖 Checking GigaChat API...")

    # aiohttp doesn't support per-request CA bundles directly;
    # use an SSLContext to pass the system CA bundle.
    import ssl
    ssl_ctx = ssl.create_default_context(cafile=_CA_BUNDLE) \
              if os.path.exists(_CA_BUNDLE) else ssl.create_default_context()

    timeout = aiohttp.ClientTimeout(total=15)
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)

    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Step 1: OAuth token
            rq_uid = str(uuid.uuid4())
            async with session.post(
                _OAUTH_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": rq_uid,
                    "Authorization": f"Basic {creds}",
                },
                data={"scope": "GIGACHAT_API_PERS"},
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    await msg.edit_text(
                        f"❌ OAuth failed (HTTP {resp.status}):\n`{body[:200]}`",
                        parse_mode="Markdown",
                    )
                    return
                token_data  = await resp.json(content_type=None)
                access_token = token_data.get("access_token")

            if not access_token:
                await msg.edit_text("❌ OAuth succeeded but `access_token` was empty.")
                return

            # Step 2: List models
            async with session.get(
                _MODELS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as resp2:
                if resp2.status != 200:
                    body = await resp2.text()
                    await msg.edit_text(
                        f"⚠️ Token OK but models endpoint returned HTTP {resp2.status}:\n`{body[:200]}`",
                        parse_mode="Markdown",
                    )
                    return
                models_data = await resp2.json(content_type=None)

        model_ids = [m.get("id", "?") for m in models_data.get("data", [])]
        if model_ids:
            models_str = "\n".join(f"  • `{mid}`" for mid in model_ids)
            await msg.edit_text(
                f"✅ *GigaChat API is UP*\n\n*Models available:*\n{models_str}",
                parse_mode="Markdown",
            )
        else:
            await msg.edit_text("✅ GigaChat API is UP — no models listed in response.")

    except aiohttp.ClientConnectorError as e:
        await msg.edit_text(
            f"❌ Connection failed:\n`{e}`\n\n"
            "Check network connectivity and CA certificates.",
            parse_mode="Markdown",
        )
    except aiohttp.ClientError as e:
        await msg.edit_text(f"❌ HTTP error: `{e}`", parse_mode="Markdown")
    except Exception as e:
        logger.error("giga_check_command error: %s", e, exc_info=True)
        await msg.edit_text(f"💥 Unexpected error: `{e}`", parse_mode="Markdown")
