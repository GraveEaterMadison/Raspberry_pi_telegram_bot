"""handlers/yandex_ocr_handler.py — Yandex Cloud IAM token check + OCR ping.

Validates that the service-account key file is correct, generates a JWT,
exchanges it for an IAM token via gRPC, and optionally sends a minimal
Vision OCR request to verify the full pipeline end-to-end.

Requires in .env:
  YANDEX_SERVICE_ACCOUNT_KEY_PATH=/path/to/sa-key.json

Usage:
  /yandex_ocr          → check IAM token only (fast)
  /yandex_ocr ping     → IAM token + minimal OCR API ping
"""

import json
import logging
import os
import time

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

_KEY_PATH = os.getenv("YANDEX_SERVICE_ACCOUNT_KEY_PATH", "")


def _load_key() -> tuple[dict | None, str]:
    """Load and validate the service-account JSON key. Returns (key_dict, error_str)."""
    if not _KEY_PATH:
        return None, "YANDEX_SERVICE_ACCOUNT_KEY_PATH not set in .env"
    if not os.path.exists(_KEY_PATH):
        return None, f"Key file not found: `{_KEY_PATH}`"
    try:
        with open(_KEY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        required = {"id", "service_account_id", "private_key"}
        missing  = required - data.keys()
        if missing:
            return None, f"Key file missing fields: `{', '.join(missing)}`"
        return data, ""
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in key file: `{e}`"
    except OSError as e:
        return None, f"Cannot read key file: `{e}`"


def _create_jwt(sa_key: dict) -> str:
    try:
        import jwt  # pyjwt[crypto]
    except ImportError:
        raise RuntimeError(
            "`pyjwt[crypto]` not installed. Run: `pip install pyjwt[crypto] cryptography`"
        )
    now = int(time.time())
    payload = {
        "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        "iss": sa_key["service_account_id"],
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(
        payload,
        sa_key["private_key"],
        algorithm="PS256",
        headers={"kid": sa_key["id"]},
    )


def _get_iam_token(jwt_token: str) -> str:
    """Exchange a JWT for an IAM token via gRPC (blocking — called in executor)."""
    try:
        import yandexcloud
        from yandex.cloud.iam.v1.iam_token_service_pb2 import CreateIamTokenRequest
        from yandex.cloud.iam.v1.iam_token_service_pb2_grpc import IamTokenServiceStub
    except ImportError:
        raise RuntimeError(
            "`yandexcloud` SDK not installed.\n"
            "Run: `pip install yandexcloud`"
        )
    sdk = yandexcloud.SDK()
    stub = sdk.client(IamTokenServiceStub)
    resp = stub.Create(CreateIamTokenRequest(jwt=jwt_token))
    if not resp.iam_token or len(resp.iam_token) < 10:
        raise RuntimeError("Received an empty or malformed IAM token.")
    return resp.iam_token


async def yandex_ocr_command(update: Update, context: CallbackContext) -> None:
    """Check Yandex Cloud IAM token validity (and optionally OCR endpoint)."""
    import asyncio

    sub = (context.args[0].lower() if context.args else "check")
    msg = await update.message.reply_text("☁️ Checking Yandex Cloud IAM...")

    # 1. Load key
    key_data, err = _load_key()
    if err:
        await msg.edit_text(f"❌ {err}", parse_mode="Markdown")
        return

    # 2. Generate JWT
    try:
        jwt_token = _create_jwt(key_data)
    except RuntimeError as e:
        await msg.edit_text(f"❌ {e}", parse_mode="Markdown")
        return
    except Exception as e:
        await msg.edit_text(f"❌ JWT signing failed: `{e}`", parse_mode="Markdown")
        return

    # 3. Exchange JWT → IAM token (blocking gRPC — run in executor)
    loop = asyncio.get_event_loop()
    try:
        iam_token = await asyncio.wait_for(
            loop.run_in_executor(None, _get_iam_token, jwt_token),
            timeout=15,
        )
    except asyncio.TimeoutError:
        await msg.edit_text("⏰ IAM token request timed out (>15s).")
        return
    except RuntimeError as e:
        await msg.edit_text(f"❌ {e}", parse_mode="Markdown")
        return
    except Exception as e:
        logger.error("Yandex IAM token error: %s", e, exc_info=True)
        await msg.edit_text(f"❌ gRPC error: `{e}`", parse_mode="Markdown")
        return

    token_preview = iam_token[:12] + "..." + iam_token[-4:]

    if sub != "ping":
        await msg.edit_text(
            f"✅ *Yandex IAM token obtained*\n\n"
            f"SA ID:   `{key_data['service_account_id']}`\n"
            f"Token:   `{token_preview}`\n\n"
            f"OCR endpoint is ready. Run `/yandex_ocr ping` to do a live API call.",
            parse_mode="Markdown",
        )
        return

    # 4. Optional: minimal OCR API ping (1×1 white pixel base64)
    import aiohttp
    import base64

    ONE_WHITE_PIXEL = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    folder_id = key_data.get("folder_id", os.getenv("YANDEX_FOLDER_ID", ""))
    if not folder_id:
        await msg.edit_text(
            f"✅ IAM token OK (`{token_preview}`)\n\n"
            "⚠️ `folder_id` not in key file and `YANDEX_FOLDER_ID` not set — skipping live OCR ping.",
            parse_mode="Markdown",
        )
        return

    await msg.edit_text("☁️ IAM token OK — sending OCR ping...")
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            async with session.post(
                "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText",
                headers={
                    "Authorization": f"Bearer {iam_token}",
                    "x-folder-id": folder_id,
                    "x-data-logging-enabled": "false",
                },
                json={
                    "mimeType": "PNG",
                    "languageCodes": ["en"],
                    "content": ONE_WHITE_PIXEL,
                },
            ) as resp:
                status = resp.status
                body   = await resp.text()

        if status in (200, 400):
            # 400 is acceptable — blank image triggers "no text found" which means
            # the endpoint is reachable and authentication worked.
            await msg.edit_text(
                f"✅ *Yandex OCR API is UP*\n\n"
                f"IAM token: `{token_preview}`\n"
                f"HTTP status: `{status}` ({'OK — text recognized' if status == 200 else 'OK — no text in image (expected for ping)'})",
                parse_mode="Markdown",
            )
        else:
            await msg.edit_text(
                f"⚠️ OCR endpoint returned HTTP `{status}`:\n```\n{body[:300]}\n```",
                parse_mode="Markdown",
            )
    except aiohttp.ClientError as e:
        await msg.edit_text(f"❌ OCR ping network error: `{e}`", parse_mode="Markdown")
    except Exception as e:
        logger.error("OCR ping error: %s", e, exc_info=True)
        await msg.edit_text(f"💥 OCR ping error: `{e}`", parse_mode="Markdown")
