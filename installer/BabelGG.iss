[Setup]
AppId={{2D8D3A86-4B10-4FE6-8915-3AF7AC91E0C7}
AppName=BabelGG
AppVersion=0.1.0
DefaultDirName={autopf}\BabelGG
DefaultGroupName=BabelGG
PrivilegesRequired=admin
OutputDir=..\installer
OutputBaseFilename=BabelGG_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\BabelGG.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\BabelGG.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\BabelGG"; Filename: "{app}\BabelGG.exe"
Name: "{autodesktop}\BabelGG"; Filename: "{app}\BabelGG.exe"

[Run]
Filename: "{app}\BabelGG.exe"; Description: "Launch BabelGG"; Flags: nowait postinstall skipifsilent
