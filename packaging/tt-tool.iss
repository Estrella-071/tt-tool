[Setup]
AppId={{74A2509B-977F-47DC-8C34-409B3CB77523}
AppName=tt tool
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}
AppPublisher=tt tool contributors
AppPublisherURL=https://github.com/Estrella-071/tt-tool
AppSupportURL=https://github.com/Estrella-071/tt-tool/issues
DefaultDirName={localappdata}\Programs\tt tool
DefaultGroupName=tt tool
DisableProgramGroupPage=yes
ShowLanguageDialog=yes
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible and not arm64
MinVersion=10.0.19045
Compression=lzma2/fast
SolidCompression=yes
SetupIconFile={#PayloadDir}\tt-tool.ico
UninstallDisplayIcon={app}\tt-tool.ico
LicenseFile={#PayloadDir}\LICENSE

[Languages]
Name: "zh_TW"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "ko"; MessagesFile: "compiler:Languages\Korean.isl"

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\tt tool"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "-I -B ""{app}\app\tt_tool_launcher.py"""; WorkingDir: "{app}"; IconFilename: "{app}\tt-tool.ico"

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: "-I -B ""{app}\app\tt_tool_launcher.py"""; WorkingDir: "{app}"; Description: "tt tool"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir, Preferences, Language: String;
begin
  if CurStep <> ssPostInstall then
    Exit;
  DataDir := ExpandConstant('{localappdata}\tt-tool\data');
  Preferences := AddBackslash(DataDir) + 'tt_tool_ui.json';
  if FileExists(Preferences) then
    Exit;
  Language := Lowercase(ActiveLanguage);
  if Language = 'zh_tw' then
    Language := 'zh_TW';
  if not ForceDirectories(DataDir) then begin
    Log('Could not create the tt tool preferences directory.');
    Exit;
  end;
  if not SaveStringToFile(Preferences, '{"language":"' + Language + '"}' + #13#10, False) then
    Log('Could not save the tt tool interface language.');
end;
