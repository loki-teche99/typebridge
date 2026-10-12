; Inno Setup Script for TypeBridge Desktop Assistant
; Generates a professional Windows Setup Installer (.exe)

#define MyAppName "TypeBridge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TypeBridge"
#define MyAppURL "https://typebridge.42web.io/"
#define MyAppExeName "TypeBridge.exe"

[Setup]
; Unique AppId for upgrade detection
AppId={{D68F23A1-7BC9-44F2-8752-9A4E9E2C8E7D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=TypeBridgeSetup-v1.0.0
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} Desktop Assistant

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start TypeBridge automatically when Windows starts"; GroupDescription: "Windows Integration:"

[Files]
Source: "dist\TypeBridge\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Launch on Windows Startup if task selected
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "TypeBridge"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Automatically register Windows Firewall inbound rule for port 8765
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""TypeBridge WSS"" dir=in action=allow protocol=TCP localport=8765 program=""{app}\{#MyAppExeName}"""; Flags: runhidden; StatusMsg: "Configuring Windows Firewall..."
; Post install run option
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove Windows Firewall rule upon uninstallation
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""TypeBridge WSS"""; Flags: runhidden; RunOnceId: "DelTypeBridgeFirewallRule"
