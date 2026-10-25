# Ricostruisce gli eseguibili e l'installer: .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
.\.venv\Scripts\python.exe app.py --make-icon g15claude.ico
.\.venv\Scripts\pyinstaller.exe --noconfirm --log-level WARN g15claude.spec
$iscc = Get-ChildItem "$env:LOCALAPPDATA\Programs\Inno Setup*\ISCC.exe", "C:\Program Files*\Inno Setup*\ISCC.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
& $iscc /Qp installer.iss
Get-ChildItem Output\*.exe | Select-Object Name, @{n = "MB"; e = { [math]::Round($_.Length / 1MB, 1) } }
