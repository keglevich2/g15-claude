"""Mostra lo stato delle sessioni di Claude Code sull'LCD della G15.

Uso:  pythonw daemon.py            (in background)
      python  daemon.py --preview  (salva preview.png invece di usare la tastiera)
"""
import ctypes
import json
import os
import sys
import time
from collections import Counter
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from g15lcd import G15LCD, WIDTH, HEIGHT

SESSIONS = Path.home() / ".claude" / "g15" / "sessions"   # scritti da hook.py
REGISTRY = Path.home() / ".claude" / "sessions"           # scritti da Claude Code (<pid>.json)
FPS = 4
ROWS = 3            # sessioni per pagina
PAGE_SECONDS = 4
HIDE_AFTER = 6 * 3600      # nascondi sessioni idle/finite ferme da 6 ore
DELETE_AFTER = 24 * 3600   # cancella file orfani (sessioni chiuse male)
RECENT_UNREGISTERED = 30 * 60  # sessioni solo-hook senza voce nel registro

FONT = ImageFont.load_default_imagefont()  # font bitmap, nitido su 1 bit
SPINNER = "|/-\\"

# priorita' per l'ordinamento: prima chi ha bisogno di te
PRIORITY = {"permission": 0, "waiting": 1, "working": 2, "done": 3, "idle": 4}


def process_start(pid):
    """Ora di creazione del processo (FILETIME) o None se non esiste piu'."""
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:  # STILL_ACTIVE
            return None
        times = [wintypes.FILETIME() for _ in range(4)]
        if not k32.GetProcessTimes(h, *[ctypes.byref(t) for t in times]):
            return 0
        return (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
    finally:
        k32.CloseHandle(h)


def load_registry():
    """Sessioni Claude Code vive, dal registro che Claude Code mantiene da se'."""
    live = {}
    for f in REGISTRY.glob("*.json"):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        start = process_start(int(r.get("pid", 0)))
        if start is None:
            continue
        # protezione dal riuso del PID: l'ora di avvio deve coincidere (tolleranza 2s)
        expected = int(r.get("procStart") or 0)
        if start and expected and abs(start - expected) > 2 * 10**7:
            continue
        live[r["sessionId"]] = r
    return live


def load_hooks(now):
    out = {}
    for f in SESSIONS.glob("*.json"):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if now - s.get("updated", 0) > DELETE_AFTER:
            f.unlink(missing_ok=True)
            continue
        out[s.get("session_id")] = s
    return out


def load_sessions(now):
    registry = load_registry()
    hooks = load_hooks(now)
    out = []

    for sid, r in registry.items():
        h = hooks.get(sid)
        reg_time = r.get("statusUpdatedAt", 0) / 1000
        status = r.get("status")
        if h and h.get("updated", 0) >= reg_time - 2:
            s = dict(h)  # gli hook sono piu' recenti e piu' dettagliati
        else:
            # nessun hook (sessione avviata prima di installarli) o hook superati
            s = {
                "state": "working" if status == "busy" else ("waiting" if status == "waiting" else "done"),
                "detail": "lavora" if status == "busy" else "",
                "since": reg_time,
                "turn_start": reg_time,
                "updated": reg_time,
            }
            if h and status == "busy" and h.get("state") == "working":
                s["turn_start"] = h.get("turn_start", reg_time)
        cwd = (h or {}).get("cwd") or r.get("cwd", "")  # l'hook ha la cartella corrente
        s["session_id"] = sid
        s["project"] = os.path.basename(cwd.rstrip("\\/")) or cwd
        s["name"] = r.get("name") or sid[:8]
        if r.get("nameSource") not in (None, "derived"):
            s["project"] = s["name"]  # nome dato a mano dall'utente
        out.append(s)

    # sessioni note solo dagli hook (es. avviate fuori dalla CLI): mostrale se recenti
    for sid, h in hooks.items():
        if sid not in registry and now - h.get("updated", 0) < RECENT_UNREGISTERED:
            out.append(dict(h, name=sid[:8]))

    # stesso nome di cartella su piu' righe: distingui col nome della sessione
    counts = Counter(s["project"] for s in out)
    for s in out:
        if counts[s["project"]] > 1:
            s["project"] = s["name"]

    out = [s for s in out if not (now - s.get("updated", 0) > HIDE_AFTER and s.get("state") in ("idle", "done"))]
    out.sort(key=lambda s: (PRIORITY.get(s.get("state"), 9), s["project"]))
    return out


def fmt_elapsed(sec):
    sec = int(max(0, sec))
    if sec < 3600:
        return f"{sec // 60}:{sec % 60:02d}"
    return f"{sec // 3600}h{sec % 3600 // 60:02d}"


def text_w(d, s):
    return d.textlength(s, font=FONT)


def fit(d, s, maxw):
    if text_w(d, s) <= maxw:
        return s
    while s and text_w(d, s + "~") > maxw:
        s = s[:-1]
    return s + "~"


def draw_icon(d, x, y, state, tick):
    """Icona 7x7 in (x, y)."""
    if state == "working":
        d.text((x + 1, y - 2), SPINNER[tick % 4], font=FONT, fill=1)
    elif state == "permission":
        if tick % 2 == 0:
            d.rectangle((x, y, x + 6, y + 6), fill=1)
            d.line((x + 3, y + 1, x + 3, y + 3), fill=0)
            d.point((x + 3, y + 5), fill=0)
        else:
            d.rectangle((x, y, x + 6, y + 6), outline=1)
    elif state == "waiting":
        d.text((x + 1, y - 2), "?", font=FONT, fill=1)
    elif state == "done":
        d.line((x, y + 3, x + 2, y + 5), fill=1)
        d.line((x + 2, y + 5, x + 6, y + 1), fill=1)
    else:  # idle
        d.line((x + 1, y + 3, x + 5, y + 3), fill=1)


def render(sessions, now, tick):
    img = Image.new("1", (WIDTH, HEIGHT), 0)
    d = ImageDraw.Draw(img)

    # barra superiore invertita
    d.rectangle((0, 0, WIDTH - 1, 8), fill=1)
    n_work = sum(s["state"] == "working" for s in sessions)
    n_need = sum(s["state"] in ("permission", "waiting") for s in sessions)
    head = f"CLAUDE {len(sessions)}"
    if n_work:
        head += f"  >{n_work}"
    if n_need:
        head += f"  !{n_need}"
    d.text((2, -2), head, font=FONT, fill=0)
    clock = time.strftime("%H:%M", time.localtime(now))
    d.text((WIDTH - 2 - text_w(d, clock), -2), clock, font=FONT, fill=0)

    if not sessions:
        msg = "nessuna sessione attiva"
        d.text(((WIDTH - text_w(d, msg)) / 2, 20), msg, font=FONT, fill=1)
        return img

    pages = (len(sessions) + ROWS - 1) // ROWS
    page = int(now // PAGE_SECONDS) % pages
    if pages > 1:
        ind = f"{page + 1}/{pages}"
        tw = text_w(d, ind)
        d.text((WIDTH - 2 - tw - 4 - text_w(d, clock), -2), ind, font=FONT, fill=0)

    for i, s in enumerate(sessions[page * ROWS:(page + 1) * ROWS]):
        y = 10 + i * 11
        st = s.get("state", "idle")
        draw_icon(d, 1, y + 2, st, tick)

        if st == "working":
            right = f"{s.get('detail', '')} {fmt_elapsed(now - s.get('turn_start', s.get('since', now)))}"
        elif st == "permission":
            right = "PERMESSO?"
        elif st == "waiting":
            right = "ti aspetta"
        elif st == "done":
            right = f"ok {fmt_elapsed(now - s.get('since', now))} fa"
        else:
            right = "pronta"
        right = fit(d, right, 78)
        rw = text_w(d, right)
        d.text((WIDTH - 1 - rw, y - 1), right, font=FONT, fill=1)
        name = fit(d, s.get("project", "?"), WIDTH - 12 - rw - 4)
        d.text((10, y - 1), name, font=FONT, fill=1)
    return img


def run(stop=None, on_status=None):
    """Aggiorna l'LCD finche' `stop` (threading.Event) non viene impostato.

    on_status(connected: bool, n_sessions: int) viene chiamato quando cambia qualcosa.
    """
    lcd = None
    tick = 0
    last = None
    status = None
    while not (stop and stop.is_set()):
        now = time.time()
        sessions = load_sessions(now)
        img = render(sessions, now, tick)
        frame = img.tobytes()
        try:
            if lcd is None:
                lcd = G15LCD()
                last = None
            if frame != last:
                lcd.show(img)
                last = frame
        except Exception:
            if lcd:
                lcd.close()
            lcd = None
        if on_status and status != (lcd is not None, len(sessions)):
            status = (lcd is not None, len(sessions))
            on_status(*status)
        tick += 1
        wait = 1 / FPS if lcd else 5  # tastiera assente: riprova piu' tardi
        if stop:
            stop.wait(wait)
        else:
            time.sleep(wait)
    if lcd:  # all'uscita lascia lo schermo vuoto
        try:
            lcd.show(Image.new("1", (WIDTH, HEIGHT), 0))
        finally:
            lcd.close()


def main():
    if "--preview" in sys.argv:
        now = time.time()
        img = render(load_sessions(now), now, 0)
        img.resize((WIDTH * 4, HEIGHT * 4), Image.NEAREST).save(Path(__file__).with_name("preview.png"))
        return
    run()


if __name__ == "__main__":
    main()
