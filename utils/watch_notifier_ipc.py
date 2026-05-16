"""utils/watch_notifier_ipc.py — Async IPC client for the watch_notifier daemon.

The daemon listens on a Unix domain socket and forwards Bluetooth messages to
paired smartwatches. This module provides both a sync and an async wrapper.
"""

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

SOCKET_PATH = os.getenv("WATCH_NOTIFIER_SOCKET", "/tmp/watch_notifier.sock")


def send_bt_message(address: str, message: str) -> bool:
    """Synchronous send — kept for backward compatibility."""
    import socket as _socket

    if not os.path.exists(SOCKET_PATH):
        logger.warning("watch_notifier socket not found: %s", SOCKET_PATH)
        return False

    try:
        with _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect(SOCKET_PATH)
            payload = json.dumps({"address": address, "message": message})
            sock.sendall(payload.encode())
            sock.shutdown(_socket.SHUT_WR)
            response = sock.recv(4096)
            if response:
                result = json.loads(response.decode())
                return result.get("status") == "ok"
    except (FileNotFoundError, ConnectionRefusedError, OSError,
            json.JSONDecodeError, KeyError, TimeoutError) as e:
        logger.debug("watch_notifier IPC error for %s: %s", address, e)
    return False


async def send_bt_message_async(address: str, message: str) -> bool:
    """Async send — runs the blocking IPC call in an executor so the bot
    event loop is never stalled waiting for the socket."""
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, send_bt_message, address, message),
            timeout=6,
        )
    except asyncio.TimeoutError:
        logger.warning("watch_notifier timeout for %s", address)
        return False
    except Exception as e:
        logger.error("watch_notifier async error: %s", e)
        return False
