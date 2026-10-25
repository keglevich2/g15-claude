# PyInstaller: due eseguibili in un'unica cartella dist\g15claude\
#   g15claude.exe       app con icona nell'area di notifica (senza console)
#   g15claude-hook.exe  hook per Claude Code (console, solo libreria standard)
# Build:  .venv\Scripts\pyinstaller --noconfirm g15claude.spec

app = Analysis(["app.py"], hiddenimports=["pystray._win32"])
hook = Analysis(["hook.py"], excludes=["PIL", "hid", "pystray", "tkinter"])

app_exe = EXE(
    PYZ(app.pure), app.scripts, [],
    exclude_binaries=True, name="g15claude", icon="g15claude.ico", console=False,
)
hook_exe = EXE(
    PYZ(hook.pure), hook.scripts, [],
    exclude_binaries=True, name="g15claude-hook", icon="g15claude.ico", console=True,
)

coll = COLLECT(
    app_exe, app.binaries, app.datas,
    hook_exe, hook.binaries, hook.datas,
    name="g15claude",
)
