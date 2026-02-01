; Inno Setup script for PtoMpy
; Build the Nuitka standalone first: python build_nuitka.py
; Then compile this script with Inno Setup (iscc setup.iss) or run: python build_setup.py

#define MyAppName "PtoMpy"
#define MyAppVersion "0.2"
#define MyAppExe "ptompy.exe"
#define BuildDist "build\main.dist"
#define MyAppIcon "icons\app.ico"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=build
OutputBaseFilename=PtoMpy_Setup_{#MyAppVersion}
SetupIconFile=icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "{#BuildDist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Explicit icon so Start Menu / Desktop show the app icon (not generic)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\{#MyAppIcon}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; IconFilename: "{app}\{#MyAppIcon}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
