#define AppGuid "{74A2509B-977F-47DC-8C34-409B3CB77523}"
#define LauncherArguments "-I -B"

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
DisableWelcomePage=no
DisableDirPage=auto
UsePreviousAppDir=yes
AllowNetworkDrive=no
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
WizardStyle=modern light windows11 hidebevels
WizardBackColor=#e9e6ee
WizardImageBackColor=#e9e6ee
WizardSmallImageBackColor=#e9e6ee
WizardImageFile=installer-art\cover.png
WizardSmallImageFile=installer-art\mark.png

[Languages]
Name: "zh_TW"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "ko"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "startmenu"; Description: "{cm:StartMenuShortcut}"
Name: "desktop"; Description: "{cm:DesktopShortcut}"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "installer-art\mark.png"; DestDir: "{app}"; DestName: "uninstall-mark.png"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{group}\tt tool.lnk"; Check: RemoveStartMenuShortcut
Type: files; Name: "{userdesktop}\tt tool.lnk"; Check: RemoveDesktopShortcut

[Icons]
Name: "{app}\tt tool"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "{#LauncherArguments} ""{app}\app\tt_tool_launcher.py"""; WorkingDir: "{app}"; IconFilename: "{app}\tt-tool.ico"
Name: "{group}\tt tool"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "{#LauncherArguments} ""{app}\app\tt_tool_launcher.py"""; WorkingDir: "{app}"; IconFilename: "{app}\tt-tool.ico"; Tasks: startmenu; Check: CanCreateStartMenuShortcut
Name: "{userdesktop}\tt tool"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "{#LauncherArguments} ""{app}\app\tt_tool_launcher.py"""; WorkingDir: "{app}"; IconFilename: "{app}\tt-tool.ico"; Tasks: desktop; Check: CanCreateDesktopShortcut

[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: "{#LauncherArguments} ""{app}\app\tt_tool_launcher.py"""; WorkingDir: "{app}"; Description: "{cm:LaunchTool}"; Flags: nowait postinstall skipifsilent unchecked

#include "tt-tool-messages.iss"

[Code]
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppGuid}_is1';
  StartMenuHash = 'StartMenuShortcutHash';
  DesktopHash = 'DesktopShortcutHash';

var
  PlaceStartMenuLink, PlaceDesktopLink: Boolean;

function PreviousInstallFolder: String;
begin
  Result := '';
  RegQueryStringValue(HKCU, UninstallKey, 'Inno Setup: App Path', Result);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  PreviousDir: String;
begin
  PreviousDir := PreviousInstallFolder;
  Result := '';
  if (PreviousDir <> '') and not PathSame(
    RemoveBackslashUnlessRoot(ExpandFileName(PreviousDir)),
    RemoveBackslashUnlessRoot(ExpandFileName(WizardDirValue))) then
    Result := CustomMessage('KeepInstallFolder');
end;

function LegacyStartMenuLink(Path: String): Boolean;
var
  Shell, Folder, Item, Link: Variant;
  PreviousDir, Target, Arguments: String;
begin
  Result := False;
  PreviousDir := PreviousInstallFolder;
  if PreviousDir = '' then
    Exit;
  try
    Shell := CreateOleObject('Shell.Application');
    Folder := Shell.NameSpace(ExtractFileDir(Path));
    Item := Folder.ParseName(ExtractFileName(Path));
    Link := Item.GetLink;
    Target := Link.Path;
    Arguments := Link.Arguments;
    Result := PathSame(Target, AddBackslash(PreviousDir) + 'runtime\pythonw.exe') and
      (Arguments = '{#LauncherArguments} "' + AddBackslash(PreviousDir) + 'app\tt_tool_launcher.py"');
  except
    Log('Could not verify the optional Start Menu shortcut; leaving it alone.');
  end;
end;

function OwnedShortcut(Path, Key: String): Boolean;
var
  SavedHash: String;
begin
  Result := False;
  if not FileExists(Path) then
    Exit;
  SavedHash := GetPreviousData(Key, '');
  if SavedHash <> '' then begin
    try
      Result := CompareText(GetSHA256OfFile(Path), SavedHash) = 0;
    except
      Log('Could not verify the optional shortcut; leaving it alone.');
    end;
  end else if Key = StartMenuHash then
    Result := LegacyStartMenuLink(Path);
end;

function RemoveStartMenuShortcut: Boolean;
begin
  Result := not WizardIsTaskSelected('startmenu') and
    OwnedShortcut(ExpandConstant('{group}\tt tool.lnk'), StartMenuHash);
end;

function RemoveDesktopShortcut: Boolean;
begin
  Result := not WizardIsTaskSelected('desktop') and
    OwnedShortcut(ExpandConstant('{userdesktop}\tt tool.lnk'), DesktopHash);
end;

function CanCreateStartMenuShortcut: Boolean;
var
  Path: String;
begin
  Path := ExpandConstant('{group}\tt tool.lnk');
  Result := not FileExists(Path) or OwnedShortcut(Path, StartMenuHash);
  PlaceStartMenuLink := Result;
end;

function CanCreateDesktopShortcut: Boolean;
var
  Path: String;
begin
  Path := ExpandConstant('{userdesktop}\tt tool.lnk');
  Result := not FileExists(Path) or OwnedShortcut(Path, DesktopHash);
  PlaceDesktopLink := Result;
end;

procedure RegisterPreviousData(PreviousDataKey: Integer);
var
  StartLink, DesktopLink: String;
begin
  StartLink := ExpandConstant('{group}\tt tool.lnk');
  DesktopLink := ExpandConstant('{userdesktop}\tt tool.lnk');
  if PlaceStartMenuLink and FileExists(StartLink) then
    SetPreviousData(PreviousDataKey, StartMenuHash, GetSHA256OfFile(StartLink));
  if PlaceDesktopLink and FileExists(DesktopLink) then
    SetPreviousData(PreviousDataKey, DesktopHash, GetSHA256OfFile(DesktopLink));
end;

procedure InitializeUninstallProgressForm;
var
  MarkFile: String;
begin
  MarkFile := ExpandConstant('{app}\uninstall-mark.png');
  if FileExists(MarkFile) then begin
    try
      UninstallProgressForm.WizardSmallBitmapImage.PngImage.LoadFromFile(MarkFile);
      UninstallProgressForm.WizardSmallBitmapImage.Stretch := True;
    except
      Log('Could not load the tt tool uninstall image.');
    end;
  end;
end;

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
