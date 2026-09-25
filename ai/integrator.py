"""ai/integrator.py — /integrate <github_url>: clones a GitHub repo, has
Claude write a skills/ wrapper for it, and only activates it after the user
taps "confirm" on the generated code. See README → AI & Extensibility.

Security model (this runs arbitrary third-party code with the bot's full
privileges — shell, files, GPIO — so it's deliberately conservative):
  * Only plain https://github.com/<owner>/<repo> URLs are accepted.
  * The generated module is written to a *pending* file outside skills/,
    so it can never be auto-loaded before a human has seen and approved it
    (skills/__init__.py only scans the skills/ package itself).
  * Dependency installation only happens after that approval, and only via
    a fixed, parameterized argv chosen by inspecting which manifest file
    exists (requirements.txt / pyproject.toml / package.json) — never a
    shell string built from repo or model content.
  * The generated code is syntax-checked before it's ever shown or run.
"""
import asyncio
import logging
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

import aiohttp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from ai import registry
from config import (
    AI_INTEGRATION_MAX_TOKENS,
    AI_MODEL,
    ANTHROPIC_API_KEY,
    INTEGRATION_CLONE_TIMEOUT,
    INTEGRATION_INSTALL_TIMEOUT,
    VENDOR_DIR,
)

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_GITHUB_RE = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
_MANIFESTS = ("requirements.txt", "pyproject.toml", "package.json", "setup.py", "Pipfile")

_PENDING_TTL = 600  # seconds
_pending: dict[str, dict] = {}

SKILL_CONTRACT = """\
A skill is a single Python module with a module-level SKILL dict:

    SKILL = {
        "name": "tool_name",                 # short, snake_case, unique
        "description": "One sentence telling the AI what it does and when to use it.",
        "kind": "data",                      # handler returns a string
        "input_schema": {
            "type": "object",
            "properties": {"args": {"type": "string", "description": "..."}},
            "required": [],
        },
        "handler": my_async_function,
    }

    async def my_async_function(update, context, tool_input: dict) -> str:
        ...  # tool_input["args"] is whatever the AI decided to pass in
        return "result text shown to the user"
"""


async def integrate_command(update: Update, context: CallbackContext) -> None:
    """Turn a GitHub repo into a new AI skill. Usage: /integrate <github-url>"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/integrate <github-url>`\nExample: `/integrate https://github.com/owner/repo`",
            parse_mode="Markdown",
        )
        return
    if not ANTHROPIC_API_KEY:
        await update.message.reply_text(
            "⚠️ `ANTHROPIC_API_KEY` is required to analyze a repo and generate skill code.",
            parse_mode="Markdown",
        )
        return

    match = _GITHUB_RE.match(context.args[0].strip())
    if not match:
        await update.message.reply_text(
            "❌ Only plain `https://github.com/<owner>/<repo>` URLs are supported.",
            parse_mode="Markdown",
        )
        return
    owner, repo = match.groups()
    url = f"https://github.com/{owner}/{repo}"
    slug = re.sub(r"[^a-z0-9_]", "_", f"{owner}_{repo}".lower())
    repo_dir = Path(VENDOR_DIR) / slug

    msg = await update.message.reply_text(f"🔍 Cloning `{owner}/{repo}`...", parse_mode="Markdown")

    try:
        await _clone(url, repo_dir)
    except Exception as e:
        await msg.edit_text(f"❌ Clone failed: `{e}`", parse_mode="Markdown")
        return

    await msg.edit_text(
        f"🧠 Analyzing `{owner}/{repo}` and writing a skill wrapper... (uses one Claude call)",
        parse_mode="Markdown",
    )

    try:
        context_blob = _summarize_repo(repo_dir)
        summary, code = await _generate_skill(url, repo_dir, context_blob)
    except Exception as e:
        logger.error("Integration analysis failed for %s: %s", url, e, exc_info=True)
        shutil.rmtree(repo_dir, ignore_errors=True)
        await msg.edit_text(f"❌ Analysis failed: `{e}`", parse_mode="Markdown")
        return

    syntax_error = _check_syntax(code)
    if syntax_error:
        shutil.rmtree(repo_dir, ignore_errors=True)
        await msg.edit_text(
            f"❌ Generated code had a syntax error, aborting:\n`{syntax_error}`",
            parse_mode="Markdown",
        )
        return

    pending_path = repo_dir / "_pending_skill.py"
    pending_path.write_text(code, encoding="utf-8")

    install_cmd = _detect_install_cmd(repo_dir)
    tool_names = re.findall(r'"name"\s*:\s*"([^"]+)"', code)

    _clean_old_pending()
    token = uuid.uuid4().hex[:12]
    _pending[token] = {
        "slug": slug,
        "repo_dir": str(repo_dir),
        "pending_path": str(pending_path),
        "install_cmd": install_cmd,
        "ts": time.monotonic(),
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Aktivieren", callback_data=f"integrate:yes:{token}"),
        InlineKeyboardButton("❌ Verwerfen", callback_data=f"integrate:no:{token}"),
    ]])
    install_note = f"\n📦 Wird vor Aktivierung ausgeführt: `{' '.join(install_cmd)}`" if install_cmd else ""
    caption = (
        f"🔌 *Vorschlag für neues Skill aus* `{owner}/{repo}`\n\n"
        f"{summary}\n\n"
        f"🛠️ Neue KI-Tools: {', '.join(f'`{n}`' for n in tool_names) or '_(keine erkannt)_'}"
        f"{install_note}\n\n"
        f"⚠️ Prüfe den angehängten Code, bevor du aktivierst — er läuft mit den vollen Rechten des Bots."
    )
    try:
        await msg.edit_text(caption, parse_mode="Markdown", reply_markup=keyboard)
    except BadRequest:
        # The AI-written summary may contain characters that break Markdown
        # parsing — fall back to plain text rather than losing the buttons.
        await msg.edit_text(caption, reply_markup=keyboard)
    await update.message.reply_document(
        document=code.encode("utf-8"),
        filename=f"{slug}_skill.py",
        caption="Generierter Skill-Code (Vorschau)",
    )


async def activate(token: str) -> dict:
    """Runs on the ✅ button. Installs deps (if any), moves the pending file
    into skills/, and hot-reloads the AI tool registry."""
    pending = _pending.pop(token, None)
    if pending is None:
        return {"ok": False, "message": "⌛ Dieser Vorschlag ist abgelaufen oder wurde bereits verwendet."}

    repo_dir = Path(pending["repo_dir"])
    if pending["install_cmd"]:
        try:
            await _run_install(pending["install_cmd"], repo_dir)
        except Exception as e:
            return {
                "ok": False,
                "message": f"❌ Installation fehlgeschlagen: `{e}`\nSkill wurde *nicht* aktiviert.",
            }

    dest = Path("skills") / f"{pending['slug']}_skill.py"
    shutil.copyfile(pending["pending_path"], dest)
    registry.reload()

    return {
        "ok": True,
        "message": f"✅ Aktiviert! Neue Datei: `skills/{dest.name}`\nDie KI kann die neuen Tools jetzt im Chat nutzen.",
    }


def discard(token: str) -> dict:
    pending = _pending.pop(token, None)
    if pending is None:
        return {"ok": False, "message": "⌛ Dieser Vorschlag ist abgelaufen oder wurde bereits verwendet."}
    shutil.rmtree(pending["repo_dir"], ignore_errors=True)
    return {"ok": True, "message": "❌ Verworfen — Repo wurde entfernt."}


def _clean_old_pending() -> None:
    now = time.monotonic()
    for tok in [t for t, p in _pending.items() if now - p["ts"] > _PENDING_TTL]:
        stale = _pending.pop(tok, None)
        if stale:
            shutil.rmtree(stale["repo_dir"], ignore_errors=True)


async def _clone(url: str, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", url, str(dest),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=INTEGRATION_CLONE_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"clone timed out after {INTEGRATION_CLONE_TIMEOUT}s")
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode(errors="replace")[:300] or "unknown git error")


def _find_readme(repo_dir: Path) -> Path | None:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        f = repo_dir / name
        if f.exists():
            return f
    return None


def _summarize_repo(repo_dir: Path) -> str:
    parts = []

    readme = _find_readme(repo_dir)
    if readme:
        parts.append("## README (truncated)\n" + readme.read_text(encoding="utf-8", errors="replace")[:4000])

    entries = sorted(
        p.relative_to(repo_dir).as_posix()
        for p in repo_dir.rglob("*")
        if p.is_file() and ".git" not in p.parts
    )
    parts.append("## File listing (truncated)\n" + "\n".join(entries[:150]))

    for name in _MANIFESTS:
        f = repo_dir / name
        if f.exists():
            parts.append(f"## {name} (truncated)\n" + f.read_text(encoding="utf-8", errors="replace")[:2000])

    return "\n\n".join(parts)[:9000]


def _check_syntax(code: str) -> str | None:
    try:
        compile(code, "<generated skill>", "exec")
        return None
    except SyntaxError as e:
        return str(e)


def _detect_install_cmd(repo_dir: Path) -> list[str] | None:
    if (repo_dir / "requirements.txt").exists():
        return [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    if (repo_dir / "pyproject.toml").exists() or (repo_dir / "setup.py").exists():
        return [sys.executable, "-m", "pip", "install", "."]
    if (repo_dir / "package.json").exists() and shutil.which("npm"):
        return ["npm", "install"]
    return None


async def _run_install(cmd: list[str], cwd: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=INTEGRATION_INSTALL_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"install timed out after {INTEGRATION_INSTALL_TIMEOUT}s")
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode(errors="replace")[:300] or "unknown install error")


_GEN_USER_TEMPLATE = (
    "Repository: {url}\n\n{context}\n\n"
    "Respond in exactly this format and nothing else:\n"
    "### SUMMARY\n<one short paragraph, in German, describing what this skill will let the AI do>\n"
    "### CODE\n```python\n<the full skill module>\n```"
)


async def _generate_skill(url: str, repo_dir: Path, context_blob: str) -> tuple[str, str]:
    system_prompt = (
        "You turn a GitHub repository into a single-file Python skill plugin for a Raspberry Pi "
        "Telegram bot.\n\n" + SKILL_CONTRACT + "\n"
        "Rules:\n"
        "- Output ONLY the two sections requested by the user, nothing else.\n"
        "- The code must be a complete, self-contained Python module.\n"
        f"- The cloned repo lives on disk at {str(repo_dir.resolve())!r} — hardcode that exact path as a "
        "string constant (e.g. REPO_DIR) and use it to run the repo's CLI via "
        "asyncio.create_subprocess_exec, or add it to sys.path and import it directly — whichever fits.\n"
        "- Never use shell=True or build a shell command string; always pass argument lists.\n"
        "- Always apply a subprocess timeout (10-30s) and truncate returned output to a few thousand characters.\n"
        "- Never delete, move, or write files outside REPO_DIR, and never touch system configuration.\n"
        "- If the repo isn't obviously automatable as a simple tool, still produce your best-effort single "
        "tool that reports its main purpose when called."
    )
    user_prompt = _GEN_USER_TEMPLATE.format(url=url, context=context_blob)

    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            _API_URL,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "max_tokens": AI_INTEGRATION_MAX_TOKENS,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=aiohttp.ClientTimeout(total=60),
        )
        if resp.status != 200:
            error = await resp.text()
            raise RuntimeError(f"Anthropic API error {resp.status}: {error[:200]}")
        data = await resp.json()
        text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")

    code_match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if not code_match:
        raise RuntimeError("Claude did not return a code block")
    summary_match = re.search(r"###\s*SUMMARY\s*(.*?)###\s*CODE", text, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else "_(keine Zusammenfassung)_"
    return summary, code_match.group(1).strip()
