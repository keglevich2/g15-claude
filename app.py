"""G15 Claude Status: icona nell'area di notifica + aggiornamento dell'LCD della G15."""
import ctypes
import sys
import threading
import winreg
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

import daemon
import hookcfg

APP_NAME = "G15 Claude Status"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def make_icon(size=64):
    """Icona: un piccolo LCD verde con un cursore."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64
    d.rounded_rectangle((2 * s, 12 * s, 62 * s, 52 * s), radius=6 * s, fill=(40, 40, 40, 255))
    d.rectangle((8 * s, 18 * s, 56 * s, 46 * s), fill=(150, 220, 60, 255))
    d.text((12 * s, 22 * s), ">_", fill=(20, 40, 10, 255), font_size=int(20 * s))
    return img


def exe_command():
    return f'"{sys.executable}"'


def autostart_enabled(_=None):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except OSError:
        return False


def toggle_autostart(icon, _item):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if autostart_enabled():
            winreg.DeleteValue(k, APP_NAME)
        else:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, exe_command())
    icon.update_menu()


def run_tray():
    # una sola istanza alla volta
    ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\G15ClaudeStatus")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return

    stop = threading.Event()
    state = {"text": "Avvio..."}

    def on_status(connected, n):
        state["text"] = f"{'G15 collegata' if connected else 'G15 non trovata'} - {n} sessioni"
        icon.title = f"{APP_NAME}\n{state['text']}"
        icon.update_menu()

    def quit_app(icon, _item):
        stop.set()
        worker.join(timeout=3)
        icon.stop()

    icon = pystray.Icon(
        "g15claude",
        make_icon(),
        APP_NAME,
        menu=pystray.Menu(
            pystray.MenuItem(lambda _: state["text"], None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Avvia con Windows", toggle_autostart, checked=autostart_enabled),
            pystray.MenuItem("Esci", quit_app),
        ),
    )
    worker = threading.Thread(target=daemon.run, args=(stop, on_status), daemon=True)
    worker.start()
    icon.run()


def main():
    args = sys.argv[1:]
    if args[:1] == ["--install-hooks"]:
        hook = args[1] if len(args) > 1 else str(Path(sys.executable).with_name("g15claude-hook.exe"))
        hookcfg.install(hook)
    elif args[:1] == ["--uninstall-hooks"]:
        hookcfg.uninstall()
    elif args[:1] == ["--make-icon"]:
        make_icon(256).save(args[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
    else:
        run_tray()


if __name__ == "__main__":
    main()
