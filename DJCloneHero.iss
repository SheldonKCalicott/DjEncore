; Inno Setup Script for DJ Clone Hero
[Setup]
AppName=DJ Clone Hero
AppVersion=1.0
DefaultDirName={autopf}\DJ Clone Hero
DefaultGroupName=DJ Clone Hero
OutputBaseFilename=DJCloneHero_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=src\app.ico
UninstallDisplayIcon={app}\DJCloneHero.exe
PrivilegesRequired=lowest
OutputDir=.

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\DJCloneHero.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\DJ Clone Hero"; Filename: "{app}\DJCloneHero.exe"
Name: "{commondesktop}\DJ Clone Hero"; Filename: "{app}\DJCloneHero.exe"

[Run]
Filename: "{app}\DJCloneHero.exe"; Description: "Launch DJ Clone Hero"; Flags: postinstall skipifsilent
