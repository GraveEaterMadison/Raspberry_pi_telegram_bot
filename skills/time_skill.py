"""skills/time_skill.py — example skill: a plain data tool (no Telegram
formatting of its own). Copy this file's shape to add new AI capabilities."""
from datetime import datetime


async def get_current_time(update, context, tool_input: dict) -> str:
    return datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")


SKILL = {
    "name": "current_time",
    "description": "Get the current date and time on the Raspberry Pi.",
    "kind": "data",
    "input_schema": {"type": "object", "properties": {}, "required": []},
    "handler": get_current_time,
}
