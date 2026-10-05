; =====================================================================
; OmniDownloader - Inno Setup 6 Windows Installer Script
; Creates modern, non-admin (per-user) Windows Setup executable
; Integrates with Start Menu, Windows Search, Desktop, and Windows Settings
; =====================================================================

#define MyAppName "OmniDownloader"
#define MyAppVersion "1.2.3"
#define MyAppPublisher "Aniket Kumar"
#define MyAppURL "https://github.com/Aniketkumar-01/socials_downloader"
#define MyAppExeName "OmniDownloader.exe"

[Setup]
; Unique GUID for OmniDownloader to manage clean updates/upgrades
AppId={{8B842F5E-3796-4A73-BD7A-A6F292B289A0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Per-User Installation: Installs to %LOCALAPPDATA%\Programs without Administrator/UAC prompt
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

; Output file name and destination
OutputDir=dist
OutputBaseFilename=OmniDownloader-Setup
SetupIconFile=assets\app.ico

; Compression settings (optimal for fast extraction)
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Uninstaller configuration for Windows Settings (Add or Remove Programs)
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon"; Description: "Create a Start Menu shortcut (accessible via Windows Search)"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Standalone compiled executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Optional assets and documentation
Source: "assets\app.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "DOCUMENTATION.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu shortcut - Indexed by Windows Search (Win + "Omni")
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "Universal Video & Playlist Downloader"; Tasks: startmenuicon
; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "Universal Video & Playlist Downloader"; Tasks: desktopicon

[Run]
; Option to launch OmniDownloader immediately after installation completes
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up runtime browser profiles on uninstall
Type: filesandordirs; Name: "{localappdata}\OmniDownloader\AppShellProfile"
Type: filesandordirs; Name: "{localappdata}\OmniDownloader\DesktopProfile"
