; Installer di G15 Claude Status (Inno Setup 6)
; Build: ISCC.exe installer.iss   ->  Output\G15ClaudeStatus-Setup-<versione>.exe

#define AppName "G15 Claude Status"
#define AppVersion "1.0.0"
#define AppExe "g15claude.exe"

[Setup]
AppId={{F79770B9-09EE-4A2B-BBC4-AFFA58674321}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=rombo
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; installazione per l'utente corrente, senza amministratore
PrivilegesRequired=lowest
OutputBaseFilename=G15ClaudeStatus-Setup-{#AppVersion}
SetupIconFile=g15claude.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=force

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "autostart"; Description: "Avvia automaticamente con Windows"
Name: "hooks"; Description: "Collega a Claude Code (aggiunge gli hook in ~/.claude/settings.json)"

[Files]
Source: "dist\g15claude\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Disinstalla {#AppName}"; Filename: "{uninstallexe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
  ValueName: "{#AppName}"; ValueData: """{app}\{#AppExe}"""; Tasks: autostart; Flags: uninsdeletevalue

[InstallDelete]
; collegamento della versione di sviluppo, sostituito dalla voce di registro
Type: files; Name: "{userstartup}\{#AppName}.lnk"

[Run]
Filename: "{app}\{#AppExe}"; Parameters: "--install-hooks ""{app}\g15claude-hook.exe"""; \
  Tasks: hooks; Flags: runhidden waituntilterminated; StatusMsg: "Collegamento a Claude Code..."
Filename: "{app}\{#AppExe}"; Description: "Avvia {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "StopApp"
Filename: "{app}\{#AppExe}"; Parameters: "--uninstall-hooks"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveHooks"

[UninstallDelete]
Type: filesandordirs; Name: "{%USERPROFILE}\.claude\g15"

[Code]
// prima di installare/aggiornare chiude l'app eventualmente in esecuzione
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, Code);
  Result := '';
end;
