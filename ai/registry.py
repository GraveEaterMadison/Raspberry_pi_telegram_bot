"""ai/registry.py — builds the Claude tool-use catalogue from the bot's own
commands (handlers/*) plus user-defined skills (skills/*).

Two kinds of tools:

  * "action" tools — existing Telegram command handlers. They reply to the
    user themselves (like they always have), so no extra Claude round-trip
    is needed after they run. This is how every built-in command becomes
    AI-callable for free.
  * "data" tools — plain async functions (see skills/) that return a string
    instead of talking to Telegram. Used for new, non-command capabilities.

Call build() once at startup with the bot's COMMANDS table; ai.agent then
uses get_tool_defs() / get_tool() to drive Claude's tool-use.
"""
import logging
from typing import Awaitable, Callable, NamedTuple

from config import AI_EXCLUDED_COMMANDS

logger = logging.getLogger(__name__)

# Commands that don't make sense as AI tools (pure greeting / meta), plus
# "integrate" — installing a new skill from a GitHub repo must always be a
# deliberate, explicit /integrate call, never something the AI decides to
# do on its own from a casual chat mention of a URL.
_ALWAYS_EXCLUDED = {"start", "integrate"}


class Tool(NamedTuple):
    name: str
    description: str
    input_schema: dict
    kind: str  # "action" | "data"
    handler: Callable[..., Awaitable]


_TOOLS: dict[str, Tool] = {}
_last_commands: list[tuple] = []

_ARGS_SCHEMA = {
    "type": "object",
    "properties": {
        "args": {
            "type": "string",
            "description": (
                "Arguments exactly as a user would type them after the Telegram "
                "command, space-separated. Leave out or use an empty string if "
                "the command takes no arguments."
            ),
        }
    },
    "required": [],
}


def build(commands: list[tuple]) -> None:
    """Populate the registry from main.py's COMMANDS table plus skills/."""
    global _last_commands
    _last_commands = commands
    _TOOLS.clear()
    excluded = _ALWAYS_EXCLUDED | set(AI_EXCLUDED_COMMANDS)

    for cmd, handler_fn, desc, _protected in commands:
        if cmd in excluded:
            continue
        doc = (handler_fn.__doc__ or "").strip()
        description = f"{desc.strip()}" + (f" ({doc})" if doc else "")
        _TOOLS[cmd] = Tool(
            name=cmd,
            description=description[:1024],
            input_schema=_ARGS_SCHEMA,
            kind="action",
            handler=handler_fn,
        )

    from skills import load_skills
    for skill in load_skills():
        name = skill["name"]
        if name in excluded:
            continue
        if name in _TOOLS:
            logger.warning("Skill %r shadows an existing command tool, skipping", name)
            continue
        _TOOLS[name] = Tool(
            name=name,
            description=skill["description"][:1024],
            input_schema=skill.get("input_schema", _ARGS_SCHEMA),
            kind=skill.get("kind", "data"),
            handler=skill["handler"],
        )

    logger.info("AI tool registry ready — %d tools", len(_TOOLS))


def get_tool_defs() -> list[dict]:
    """Anthropic `tools` array, with prompt-caching on the last entry."""
    defs = [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in _TOOLS.values()
    ]
    if defs:
        defs[-1] = {**defs[-1], "cache_control": {"type": "ephemeral"}}
    return defs


def get_tool(name: str) -> Tool | None:
    return _TOOLS.get(name)


def reload() -> None:
    """Re-scan skills/ (e.g. after a new /integrate activation) without
    needing main.py's COMMANDS table passed in again."""
    build(_last_commands)
