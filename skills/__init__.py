"""skills/ — drop-in extension point for the AI.

To add a new capability the AI can use, create a new .py file in this
folder that defines a module-level ``SKILL`` dict:

    SKILL = {
        "name": "current_time",          # tool name Claude will call
        "description": "Get the current date and time on the Pi.",
        "kind": "data",                  # "data": handler returns a string
                                          # "action": handler replies via Telegram itself
        "input_schema": {                # optional, defaults to a free-text "args" string
            "type": "object", "properties": {}, "required": [],
        },
        "handler": my_async_function,
    }

For kind="data", the handler signature is:
    async def my_async_function(update, context, tool_input: dict) -> str

For kind="action", it's the same signature as any command handler:
    async def my_async_function(update, context) -> None
    (it must reply to the user itself, e.g. via update.message.reply_text)

No other wiring is needed — main.py calls ai.registry.build() once at
startup, which imports every module in this folder and picks up its
SKILL (or SKILLS, for a list of several) dict automatically.
"""
import importlib
import logging
import pkgutil

logger = logging.getLogger(__name__)


def load_skills() -> list[dict]:
    skills: list[dict] = []
    for _finder, module_name, _is_pkg in pkgutil.iter_modules(__path__):
        if module_name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{module_name}")
        except Exception:
            logger.exception("Failed to load skill module %r", module_name)
            continue

        found = getattr(module, "SKILLS", None) or (
            [module.SKILL] if hasattr(module, "SKILL") else []
        )
        for skill in found:
            if {"name", "description", "handler"} <= skill.keys():
                skills.append(skill)
            else:
                logger.warning("Skipping malformed skill in %r", module_name)
    return skills
