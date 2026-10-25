"""Aggiunge/rimuove gli hook di G15 Claude Status in ~/.claude/settings.json.

Uso: g15claude.exe --install-hooks <percorso di g15claude-hook.exe>
     g15claude.exe --uninstall-hooks
"""
import json
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"
EVENTS = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Notification", "Stop", "SessionEnd"]
TOOL_EVENTS = ("PreToolUse", "PostToolUse")
# riconosce sia gli hook dell'installer sia quelli della versione di sviluppo con python
MARKERS = ("g15claude-hook", "g15-claude/hook.py", "g15-claude\\hook.py")


def _is_ours(entry):
    return any(any(m in h.get("command", "") for m in MARKERS) for h in entry.get("hooks", []))


def _load():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _save(settings):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(SETTINGS)


def _strip(settings):
    hooks = settings.get("hooks", {})
    for ev in list(hooks):
        hooks[ev] = [e for e in hooks[ev] if not _is_ours(e)]
        if not hooks[ev]:
            del hooks[ev]
    if not hooks:
        settings.pop("hooks", None)


def install(hook_exe):
    settings = _load()
    _strip(settings)
    cmd = '"' + str(Path(hook_exe).resolve()).replace("\\", "/") + '"'
    hooks = settings.setdefault("hooks", {})
    for ev in EVENTS:
        entry = {"hooks": [{"type": "command", "command": cmd, "timeout": 5}]}
        if ev in TOOL_EVENTS:
            entry["matcher"] = "*"
        hooks.setdefault(ev, []).append(entry)
    _save(settings)


def uninstall():
    if SETTINGS.exists():
        settings = _load()
        _strip(settings)
        _save(settings)
