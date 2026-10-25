"""Hook di Claude Code: registra lo stato di ogni sessione in ~/.claude/g15/sessions/<id>.json.

Configurato in ~/.claude/settings.json per gli eventi SessionStart, UserPromptSubmit,
PreToolUse, PostToolUse, Notification, Stop, SessionEnd. Non deve mai far fallire Claude:
qualsiasi errore viene ignorato ed esce sempre con codice 0.
"""
import json
import os
import sys
import time
from pathlib import Path

SESSIONS = Path.home() / ".claude" / "g15" / "sessions"


def main():
    data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))  # tollera il BOM
    sid = data.get("session_id")
    if not sid:
        return
    event = data.get("hook_event_name", "")
    path = SESSIONS / f"{sid}.json"

    if event == "SessionEnd":
        path.unlink(missing_ok=True)
        return

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}

    now = time.time()
    cwd = data.get("cwd") or state.get("cwd") or ""
    prev = state.get("state")

    if event == "SessionStart":
        new, detail = "idle", ""
    elif event == "UserPromptSubmit":
        new, detail = "working", "pensando"
    elif event == "PreToolUse":
        new, detail = "working", data.get("tool_name", "")
    elif event == "PostToolUse":
        new, detail = "working", "pensando"
    elif event == "Notification":
        msg = (data.get("message") or "").lower()
        if "permission" in msg or "permesso" in msg:
            new, detail = "permission", data.get("message", "")
        else:
            new, detail = "waiting", "attende input"
    elif event == "Stop":
        new, detail = "done", "finito"
    else:
        return

    state.update(
        session_id=sid,
        cwd=cwd,
        project=os.path.basename(cwd.rstrip("\\/")) or cwd,
        state=new,
        detail=detail,
        updated=now,
    )
    if new != prev or "since" not in state:
        state["since"] = now
    if event == "UserPromptSubmit":
        state["turn_start"] = now

    SESSIONS.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
