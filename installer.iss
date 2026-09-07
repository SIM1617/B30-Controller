; B30 Controller - Inno Setup Script
; Need: Inno Setup 6 (https://jrsoftware.org/isinfo.php)
; Build: after build_exe.bat or build_secure.bat, compile this file in Inno Setup

#define MyAppName "B30 Controller"
#define MyAppVersion "1.0"
#define MyAppPublisher "B30"
#define MyAppExeName "B30Controller.exe"

[Setup]
AppId={{B30-Controller-2026}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=D:\Projects\installer
OutputBaseFilename=setup_B30Controller_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=D:\Projects\B30.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "D:\Projects\dist\B30Controller.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\Projects\B30.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\Projects\addresses.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\Projects\crash.log"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\B30.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\B30.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
