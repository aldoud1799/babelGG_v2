[Setup]
AppId={{2D8D3A86-4B10-4FE6-8915-3AF7AC91E0C7}
AppName=BabelGG
AppVersion=0.1.0
AppPublisher=AbeSoft
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/
DefaultDirName={autopf64}\BabelGG
DefaultGroupName=BabelGG
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\installer
OutputBaseFilename=BabelGG_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\babelgg.ico
WizardImageFile=..\assets\installer_wizard.bmp
WizardSmallImageFile=..\assets\installer_wizard_small.bmp
ChangesAssociations=no
UninstallDisplayIcon={app}\BabelGG.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\BabelGG\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Icons]
Name: "{group}\BabelGG"; Filename: "{app}\BabelGG.exe"
Name: "{autodesktop}\BabelGG"; Filename: "{app}\BabelGG.exe"; Tasks: desktopicon

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\BabelGG"

[Run]
Filename: "{app}\BabelGG.exe"; Description: "Launch BabelGG now"; Flags: nowait postinstall skipifsilent
