// SPDX-License-Identifier: GPL-3.0-only
const
  ShellColor = $00EEE6E9;
  CardColor = $00FAF7F9;
  HeaderColor = $00402B30;
  InkColor = $00402B30;
  MutedColor = $00705A62;
  DwmCornerPreference = 33;
  DwmCaptionColor = 35;
  DwmTextColor = 36;
  DwmRound = 2;
  WmPaint = $000F;
  WmQuit = $0012;
  WmNcDestroy = $0082;
  WmWindowPosChanging = $0046;
  WmWindowPosChanged = $0047;
  WmTimer = $0113;
  FileDirectory = $10;
  FileReparsePoint = $400;
  ClientAreaAnimation = $1042;
  ExtendedStyleIndex = -20;
  LayeredStyle = $00080000;
  AlphaEffect = $02;
  HideWindowPosition = $0080;
  FadeTimer = $5454;
  RevealTime = 180;
  DismissTime = 140;
  AppRunningMutex = 'Estrella071.tt-tool.Running';
  AppCloseEvent = 'Estrella071.tt-tool.Close';
  EventModifyState = $0002;

type
  TScreenPoint = record
    X, Y: Integer;
  end;
  TStatusMessage = record
    Window: HWND;
    MessageId, AlignmentPadding: Cardinal;
    WParam: NativeUInt;
    LParam: NativeInt;
    Tick: Cardinal;
    Point: TScreenPoint;
    Reserved: Cardinal;
  end;

function SetDwmAttribute(Wnd: HWND; Attribute: Cardinal; var Value: Cardinal; ValueSize: Cardinal): Longint;
  external 'DwmSetWindowAttribute@dwmapi.dll stdcall';
function AddWindowSubclass(Wnd: HWND; Callback: NativeInt; Id, Data: NativeUInt): Boolean;
  external 'SetWindowSubclass@comctl32.dll stdcall';
function RemoveWindowSubclass(Wnd: HWND; Callback: NativeInt; Id: NativeUInt): Boolean;
  external 'RemoveWindowSubclass@comctl32.dll stdcall';
function ContinueWindowMessage(Wnd: HWND; Message: Cardinal; WParam: NativeUInt; LParam: NativeInt): NativeInt;
  external 'DefSubclassProc@comctl32.dll stdcall';
function FileAttributes(const Path: String): Integer;
  external 'GetFileAttributesW@kernel32.dll stdcall';
function ReadAnimationSetting(Action, Param: Cardinal; var Enabled: Longint; Flags: Cardinal): Longint;
  external 'SystemParametersInfoW@user32.dll stdcall';
function ReadWindowStyle(Wnd: HWND; Index: Integer): NativeInt;
  external 'GetWindowLongPtrW@user32.dll stdcall';
function WriteWindowStyle(Wnd: HWND; Index: Integer; Value: NativeInt): NativeInt;
  external 'SetWindowLongPtrW@user32.dll stdcall';
function WindowOpacity(Wnd: HWND; Color: Cardinal; Alpha: Byte; Flags: Cardinal): Longint;
  external 'SetLayeredWindowAttributes@user32.dll stdcall';
function IsShown(Wnd: HWND): Longint;
  external 'IsWindowVisible@user32.dll stdcall';
function StartWindowTimer(Wnd: HWND; Id: NativeUInt; Interval: Cardinal; Callback: NativeInt): NativeUInt;
  external 'SetTimer@user32.dll stdcall';
function StopWindowTimer(Wnd: HWND; Id: NativeUInt): Longint;
  external 'KillTimer@user32.dll stdcall';
function WindowsTick: Int64;
  external 'GetTickCount64@kernel32.dll stdcall';
procedure CopyPositionFlags(var Target: Cardinal; Source, Size: NativeUInt);
  external 'RtlMoveMemory@ntdll.dll stdcall';
function OpenApplicationEvent(Access: Cardinal; Inherit: Longint; const Name: String): NativeUInt;
  external 'OpenEventW@kernel32.dll stdcall';
function SignalApplicationEvent(Event: NativeUInt): Longint;
  external 'SetEvent@kernel32.dll stdcall';
function CloseApplicationEvent(Event: NativeUInt): Longint;
  external 'CloseHandle@kernel32.dll stdcall';
function ReadStatusMessage(var Message: TStatusMessage; Window: HWND; Low, High, Remove: Cardinal): Longint;
  external 'PeekMessageW@user32.dll stdcall';
function PaintStatusMessage(var Message: TStatusMessage): NativeInt;
  external 'DispatchMessageW@user32.dll stdcall';
procedure RestoreQuitMessage(ExitCode: Integer);
  external 'PostQuitMessage@user32.dll stdcall';

type
  TRemovalShortcut = record
    Path, Hash: String;
  end;

var
  FadeCallback, OriginalExtendedStyle: NativeInt;
  FadingWindow: HWND;
  FadeStarted: Int64;
  CurrentAlpha: Byte;
  ClosingFade: Boolean;
  ClearUserData: Boolean;
  RemovalDataComplete: Boolean;
  RemovalShortcuts: array of TRemovalShortcut;

function LegacyStartMenuLink(Path: String): Boolean;
  forward;

procedure Place(Control: TControl; X, Y, Width, Height: Integer);
begin
  Control.Align := alNone;
  Control.SetBounds(ScaleX(X), ScaleY(Y), ScaleX(Width), ScaleY(Height));
end;

procedure Surface(Panel: TPanel; Fill: TColor);
begin
  Panel.BevelInner := bvNone;
  Panel.BevelOuter := bvNone;
  Panel.StyleElements := [];
  Panel.ParentBackground := False;
  Panel.Color := Fill;
end;

function SetupUIFont: String;
begin
  Result := 'Segoe UI';
  if ActiveLanguage = 'zh_TW' then
    Result := 'Microsoft JhengHei UI'
  else if ActiveLanguage = 'ja' then
    Result := 'Yu Gothic UI'
  else if ActiveLanguage = 'ko' then
    Result := 'Malgun Gothic';
end;

procedure LabelFace(LabelText: TNewStaticText; Size: Integer; Foreground: TColor; Heading: Boolean);
begin
  LabelText.AutoSize := False;
  LabelText.WordWrap := True;
  if not HighContrastActive then begin
    LabelText.StyleElements := [];
    LabelText.Font.Color := Foreground;
    LabelText.Font.Name := SetupUIFont;
  end;
  LabelText.Font.Size := Size;
  if Heading then
    LabelText.Font.Style := [fsBold];
end;

function MotionEnabled: Boolean;
var
  Enabled: Longint;
begin
  Result := False;
  if HighContrastActive then
    Exit;
  Enabled := 0;
  if ReadAnimationSetting(ClientAreaAnimation, 0, Enabled, 0) <> 0 then
    Result := Enabled <> 0;
end;

procedure ApplyWindowChrome(Wnd: HWND);
  forward;

procedure CompleteReveal(Wnd: HWND);
begin
  StopWindowTimer(Wnd, FadeTimer);
  CurrentAlpha := 255;
  WindowOpacity(Wnd, 0, CurrentAlpha, AlphaEffect);
  WriteWindowStyle(Wnd, ExtendedStyleIndex, OriginalExtendedStyle);
  ApplyWindowChrome(Wnd);
end;

procedure DismissWindow(Wnd: HWND);
var
  Start: Int64;
  Elapsed: Integer;
  FromAlpha: Byte;
  Progress: Double;
begin
  if ClosingFade or (IsShown(Wnd) = 0) or not MotionEnabled then
    Exit;
  ClosingFade := True;
  StopWindowTimer(Wnd, FadeTimer);
  WriteWindowStyle(Wnd, ExtendedStyleIndex, OriginalExtendedStyle or LayeredStyle);
  FromAlpha := CurrentAlpha;
  Start := WindowsTick;
  repeat
    Elapsed := Integer(WindowsTick - Start);
    if Elapsed > DismissTime then
      Elapsed := DismissTime;
    Progress := Double(Elapsed) / DismissTime;
    WindowOpacity(Wnd, 0, Byte(Round(FromAlpha * (1 - Progress * Progress * Progress))), AlphaEffect);
    if Elapsed < DismissTime then
      Sleep(12);
  until Elapsed >= DismissTime;
end;

function FadeWindowProc(Wnd: HWND; Message: Cardinal; WParam: NativeUInt;
  LParam: NativeInt; Id, Data: NativeUInt): NativeInt;
var
  Remaining: Double;
  Elapsed: Int64;
  Flags: Cardinal;
begin
  if (Message = WmTimer) and (WParam = FadeTimer) then begin
    if IsShown(Wnd) <> 0 then begin
      if FadeStarted = 0 then
        FadeStarted := WindowsTick;
      Elapsed := WindowsTick - FadeStarted;
      if (Elapsed >= RevealTime) or not MotionEnabled then
        CompleteReveal(Wnd)
      else begin
        Remaining := 1 - Double(Elapsed) / RevealTime;
        CurrentAlpha := Byte(Round(255 * (1 - Remaining * Remaining * Remaining)));
        WindowOpacity(Wnd, 0, CurrentAlpha, AlphaEffect);
      end;
    end;
    Result := 0;
    Exit;
  end;
  if (Message = WmWindowPosChanging) and (LParam <> 0) then begin
    { x64 WINDOWPOS has two 8-byte HWNDs and four 4-byte coordinates before flags. }
    CopyPositionFlags(Flags, NativeUInt(LParam) + 32, 4);
    if Flags and HideWindowPosition <> 0 then
      DismissWindow(Wnd);
  end;
  if (Message = WmWindowPosChanged) and ClosingFade and (IsShown(Wnd) = 0) then
    CompleteReveal(Wnd);
  if Message = WmNcDestroy then begin
    StopWindowTimer(Wnd, FadeTimer);
    RemoveWindowSubclass(Wnd, FadeCallback, Id);
    FadingWindow := 0;
  end;
  Result := ContinueWindowMessage(Wnd, Message, WParam, LParam);
end;

procedure BeginReveal(Window: TForm);
var
  Wnd: HWND;
begin
  if not MotionEnabled then
    Exit;
  Wnd := Window.Handle;
  if FadeCallback = 0 then
    FadeCallback := CreateCallback(@FadeWindowProc);
  if not AddWindowSubclass(Wnd, FadeCallback, 3, 0) then
    Exit;
  FadingWindow := Wnd;
  FadeStarted := 0;
  ClosingFade := False;
  CurrentAlpha := 0;
  OriginalExtendedStyle := ReadWindowStyle(Wnd, ExtendedStyleIndex);
  WriteWindowStyle(Wnd, ExtendedStyleIndex, OriginalExtendedStyle or LayeredStyle);
  if (WindowOpacity(Wnd, 0, CurrentAlpha, AlphaEffect) = 0) or
    (StartWindowTimer(Wnd, FadeTimer, 15, 0) = 0) then
    CompleteReveal(Wnd);
end;

procedure RemoveActiveSubclasses;
begin
  if FadingWindow <> 0 then begin
    CompleteReveal(FadingWindow);
    RemoveWindowSubclass(FadingWindow, FadeCallback, 3);
  end;
end;

procedure DeinitializeSetup;
begin
  RemoveActiveSubclasses;
end;

procedure DeinitializeUninstall;
begin
  RemoveActiveSubclasses;
end;

function TextLabel(Parent: TWinControl; Caption: String; X, Y, Width, Height, Size: Integer;
  Foreground: TColor; Heading: Boolean): TNewStaticText;
begin
  Result := TNewStaticText.Create(Parent);
  Result.Parent := Parent;
  Result.Caption := Caption;
  Result.ShowAccelChar := False;
  Result.TabStop := False;
  if HighContrastActive then
    Foreground := clWindowText;
  LabelFace(Result, Size, Foreground, Heading);
  Place(Result, X, Y, Width, Height);
end;

procedure ApplyWindowChrome(Wnd: HWND);
var
  Value: Cardinal;
begin
  { Let Windows draw the caption, shadow and rounded corners. Windows 10
    retains its native frame when the Windows 11 attributes are unavailable. }
  Value := DwmRound;
  SetDwmAttribute(Wnd, DwmCornerPreference, Value, 4);
  Value := HeaderColor;
  SetDwmAttribute(Wnd, DwmCaptionColor, Value, 4);
  Value := $00FFFFFF;
  SetDwmAttribute(Wnd, DwmTextColor, Value, 4);
end;

procedure Frame(Window: TForm; Width, Height: Integer);
begin
  if HighContrastActive then
    Exit;
  Window.StyleElements := [];
  Window.BorderStyle := bsDialog;
  Window.Position := poScreenCenter;
  Window.ClientWidth := ScaleX(Width);
  Window.ClientHeight := ScaleY(Height);
  Window.Color := ShellColor;
  ApplyWindowChrome(Window.Handle);
end;

procedure LayoutBody(Body: TNewNotebookPage);
begin
  Body.StyleElements := [];
  Body.ParentBackground := False;
  Body.Color := CardColor;
end;

procedure LayoutDirectoryControls;
var
  PageWidth, BrowseWidth, EditWidth: Integer;
begin
  { Inno aligns a notebook page when it is shown. Use the live width and undo
    the original right-anchor offsets before positioning the native controls. }
  PageWidth := WizardForm.SelectDirPage.Width;
  BrowseWidth := WizardForm.CalculateButtonWidth([WizardForm.DirBrowseButton.Caption]);
  if BrowseWidth < ScaleX(130) then
    BrowseWidth := ScaleX(130);
  EditWidth := PageWidth - BrowseWidth - ScaleX(12);
  WizardForm.DirEdit.Anchors := [akLeft, akTop];
  WizardForm.DirBrowseButton.Anchors := [akLeft, akTop];
  WizardForm.DirEdit.SetBounds(0, ScaleY(26), EditWidth, ScaleY(36));
  WizardForm.DirBrowseButton.SetBounds(PageWidth - BrowseWidth, ScaleY(24),
    BrowseWidth, ScaleY(40));
end;

procedure InitializeWizard;
var
  I: Integer;
  Card: TPanel;
begin
  if WizardSilent or HighContrastActive then
    Exit;
  WizardForm.Caption := 'tt tool · ' + CustomMessage('InstallMode');
  Frame(WizardForm, 704, 450);
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
  WizardForm.MainPanel.Visible := False;
  WizardForm.WizardBitmapImage.Visible := False;
  WizardForm.WizardBitmapImage2.Visible := False;
  WizardForm.SelectDirBitmapImage.Visible := False;

  Card := TPanel.Create(WizardForm);
  Card.Parent := WizardForm;
  Place(Card, 20, 18, 664, 360);
  Surface(Card, CardColor);

  WizardForm.OuterNotebook.Parent := Card;
  WizardForm.OuterNotebook.Anchors := [akLeft, akTop];
  Place(WizardForm.OuterNotebook, 0, 0, 664, 360);
  for I := 0 to WizardForm.OuterNotebook.PageCount - 1 do
    LayoutBody(WizardForm.OuterNotebook.Pages[I]);
  for I := 0 to WizardForm.InnerNotebook.PageCount - 1 do
    LayoutBody(WizardForm.InnerNotebook.Pages[I]);
  WizardForm.InnerNotebook.Anchors := [akLeft, akTop];
  Place(WizardForm.InnerNotebook, 28, 82, 608, 258);

  WizardForm.PageNameLabel.Parent := WizardForm.InnerPage;
  Place(WizardForm.PageNameLabel, 28, 20, 608, 39);
  LabelFace(WizardForm.PageNameLabel, 22, InkColor, True);
  WizardForm.PageDescriptionLabel.Parent := WizardForm.InnerPage;
  Place(WizardForm.PageDescriptionLabel, 28, 60, 608, 24);
  LabelFace(WizardForm.PageDescriptionLabel, 11, MutedColor, False);

  WizardForm.WelcomeLabel1.Caption := SetupMessage(msgWelcomeLabel1);
  WizardForm.WelcomeLabel2.Caption := SetupMessage(msgWelcomeLabel2);
  Place(WizardForm.WelcomeLabel1, 28, 40, 608, 54);
  LabelFace(WizardForm.WelcomeLabel1, 28, InkColor, True);
  Place(WizardForm.WelcomeLabel2, 28, 106, 560, 95);
  LabelFace(WizardForm.WelcomeLabel2, 13, MutedColor, False);
  Place(WizardForm.FinishedHeadingLabel, 28, 40, 608, 54);
  LabelFace(WizardForm.FinishedHeadingLabel, 26, InkColor, True);
  Place(WizardForm.FinishedLabel, 28, 106, 608, 72);
  LabelFace(WizardForm.FinishedLabel, 12, MutedColor, False);
  Place(WizardForm.RunList, 28, 183, 608, 95);
  Place(WizardForm.YesRadio, 28, 183, 608, 34);
  Place(WizardForm.NoRadio, 28, 221, 608, 34);

  WizardForm.SelectDirLabel.Visible := False;
  WizardForm.SelectDirBrowseLabel.Visible := False;
  WizardForm.DirEdit.AutoSize := False;
  WizardForm.DirEdit.Font.Name := SetupUIFont;
  WizardForm.DirEdit.Font.Size := 11;
  Place(WizardForm.DiskSpaceLabel, 0, 82, 608, 28);
  LabelFace(WizardForm.DiskSpaceLabel, 10, MutedColor, False);
  LayoutDirectoryControls;

  Place(WizardForm.SelectTasksLabel, 0, 8, 608, 51);
  LabelFace(WizardForm.SelectTasksLabel, 11, InkColor, False);
  Place(WizardForm.TasksList, 0, 65, 608, 166);
  WizardForm.TasksList.MinItemHeight := ScaleY(38);
  WizardForm.TasksList.BorderStyle := bsNone;
  WizardForm.TasksList.Color := CardColor;
  Place(WizardForm.ReadyLabel, 0, 8, 608, 39);
  LabelFace(WizardForm.ReadyLabel, 11, InkColor, False);
  Place(WizardForm.ReadyMemo, 0, 51, 608, 179);
  WizardForm.ReadyMemo.Font.Size := 11;
  Place(WizardForm.StatusLabel, 0, 35, 608, 32);
  LabelFace(WizardForm.StatusLabel, 12, InkColor, False);
  Place(WizardForm.ProgressGauge, 0, 75, 608, 21);
  Place(WizardForm.FilenameLabel, 0, 111, 608, 54);
  LabelFace(WizardForm.FilenameLabel, 10, MutedColor, False);
  Place(WizardForm.PreparingErrorBitmapImage, 0, 8, 32, 32);
  Place(WizardForm.PreparingLabel, 46, 8, 562, 78);
  Place(WizardForm.PreparingMemo, 0, 92, 608, 151);
  Place(WizardForm.PreparingYesRadio, 46, 114, 562, 30);
  Place(WizardForm.PreparingNoRadio, 46, 151, 562, 30);

  Place(WizardForm.CancelButton, 20, 393, 142, 41);
  Place(WizardForm.BackButton, 378, 393, 146, 41);
  Place(WizardForm.NextButton, 538, 393, 146, 41);
  BeginReveal(WizardForm);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpSelectDir) and not WizardSilent and not HighContrastActive then
    LayoutDirectoryControls;
end;

function HasUninstallSwitch(Switch: String): Boolean;
var
  I: Integer;
begin
  Result := True;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Switch) = 0 then
      Exit;
  Result := False;
end;

function ConfirmRemoval: Boolean;
var
  Dialog: TSetupForm;
  Card: TPanel;
  Directory: TNewEdit;
  Toggle: TNewCheckBox;
  Cancel, Remove: TNewButton;
begin
  Dialog := CreateCustomForm(610, 318, True, True);
  try
    Dialog.Caption := 'tt tool · ' + CustomMessage('RemoveMode');
    Dialog.Position := poScreenCenter;
    Frame(Dialog, 610, 318);
    Card := TPanel.Create(Dialog);
    Card.Parent := Dialog;
    Place(Card, 20, 20, 570, 222);
    if not HighContrastActive then
      Surface(Card, CardColor);
    TextLabel(Card, CustomMessage('RemoveHeading'), 24, 12, 522, 47, 24, InkColor, True);
    TextLabel(Card, CustomMessage('RemoveDescription'), 24, 60, 522, 46, 12, MutedColor, False);
    TextLabel(Card, CustomMessage('RemoveFolderLabel'), 24, 111, 522, 23, 10, MutedColor, False);
    Directory := TNewEdit.Create(Card);
    Directory.Parent := Card;
    Directory.ReadOnly := True;
    Directory.AutoSize := False;
    Directory.Font.Name := SetupUIFont;
    Directory.Font.Size := 11;
    Directory.Text := ExpandConstant('{app}');
    Place(Directory, 24, 136, 522, 33);
    Toggle := TNewCheckBox.Create(Card);
    Toggle.Parent := Card;
    Toggle.Caption := CustomMessage('RemoveDataOption');
    Toggle.Checked := False;
    Toggle.Font.Name := SetupUIFont;
    Toggle.Font.Size := 11;
    Place(Toggle, 24, 177, 522, 32);
    Cancel := TNewButton.Create(Dialog);
    Cancel.Parent := Dialog;
    Cancel.Caption := SetupMessage(msgButtonCancel);
    Cancel.ModalResult := mrCancel;
    Cancel.Cancel := True;
    Cancel.Default := True;
    Place(Cancel, 20, 257, 142, 44);
    Remove := TNewButton.Create(Dialog);
    Remove.Parent := Dialog;
    Remove.Caption := CustomMessage('RemoveAction');
    Remove.ModalResult := mrOk;
    Place(Remove, 424, 257, 166, 44);
    Dialog.ActiveControl := Cancel;
    BeginReveal(Dialog);
    Result := Dialog.ShowModal = mrOk;
    ClearUserData := Result and Toggle.Checked;
  finally
    Dialog.Free;
  end;
end;

function OpenRemovalNotice(const Heading, Detail: String): TSetupForm;
var
  Card: TPanel;
  Progress: TNewProgressBar;
begin
  Result := CreateCustomForm(610, 173, True, True);
  Result.Caption := 'tt tool · ' + CustomMessage('RemoveMode');
  Result.Position := poScreenCenter;
  Frame(Result, 610, 173);
  Card := TPanel.Create(Result);
  Card.Parent := Result;
  Place(Card, 20, 20, 570, 132);
  if not HighContrastActive then
    Surface(Card, CardColor);
  TextLabel(Card, Heading, 24, 12, 522, 42, 24, InkColor, True);
  TextLabel(Card, Detail, 24, 55, 522, 44, 11, MutedColor, False);
  Progress := TNewProgressBar.Create(Card);
  Progress.Parent := Card;
  Progress.Style := npbstMarquee;
  Place(Progress, 24, 103, 522, 16);
  BeginReveal(Result);
  Result.Show;
end;

procedure PaintRemovalNotice(Notice: TSetupForm);
var
  I: Integer;
  Message: TStatusMessage;
  HasMessage: Boolean;
begin
  for I := 1 to 24 do begin
    HasMessage := ReadStatusMessage(Message, Notice.Handle, WmPaint, WmPaint, 1) <> 0;
    if not HasMessage then
      HasMessage := ReadStatusMessage(Message, Notice.Handle, WmTimer, WmTimer, 1) <> 0;
    if not HasMessage then
      Exit;
    if Message.MessageId = WmQuit then begin
      RestoreQuitMessage(Integer(Message.WParam));
      Exit;
    end;
    PaintStatusMessage(Message);
  end;
end;

procedure WaitForApplicationExit(Timeout: Cardinal);
var
  Deadline: Int64;
  Notice: TSetupForm;
begin
  if not CheckForMutexes(AppRunningMutex) then
    Exit;
  Deadline := WindowsTick + Int64(Timeout);
  Notice := OpenRemovalNotice(CustomMessage('RemoveClosingHeading'), CustomMessage('RemoveClosingDetail'));
  try
    while CheckForMutexes(AppRunningMutex) and (WindowsTick < Deadline) do begin
      PaintRemovalNotice(Notice);
      Sleep(25);
    end;
  finally
    Notice.Hide;
    Notice.Free;
  end;
end;

procedure RequestApplicationExit;
var
  Event: NativeUInt;
begin
  Event := OpenApplicationEvent(EventModifyState, 0, AppCloseEvent);
  if Event = 0 then begin
    Log('App close event is unavailable; Inno will check whether tt tool is still running.');
    Exit;
  end;
  try
    if SignalApplicationEvent(Event) <> 0 then
      WaitForApplicationExit(5000)
    else
      Log('App close event could not be signaled; Inno will recheck the app mutex.');
  finally
    CloseApplicationEvent(Event);
  end;
end;

function InitializeUninstall: Boolean;
begin
  RemovalDataComplete := True;
  ClearUserData := HasUninstallSwitch('/TTTOOLCLEARDATA');
  Result := True;
  if HasUninstallSwitch('/VERYSILENT') then
    Exit;
  if HasUninstallSwitch('/TTTOOLCOMPLETE') then
    WaitForApplicationExit(2000);
  if HasUninstallSwitch('/TTTOOLPROMPT') then begin
    Result := ConfirmRemoval;
    if Result and CheckForMutexes(AppRunningMutex) then begin
      Result := MsgBox(CustomMessage('RemoveAskToCloseRunning'), mbConfirmation,
        MB_YESNO or MB_DEFBUTTON2) = IDYES;
      if Result then
        RequestApplicationExit;
    end;
  end;
end;

procedure InitializeUninstallProgressForm;
var
  Card: TPanel;
begin
  if HighContrastActive or HasUninstallSwitch('/VERYSILENT') then
    Exit;
  UninstallProgressForm.Caption := 'tt tool · ' + CustomMessage('RemoveMode');
  Frame(UninstallProgressForm, 610, 226);
  UninstallProgressForm.Bevel.Visible := False;
  UninstallProgressForm.Bevel1.Visible := False;
  UninstallProgressForm.MainPanel.Visible := False;
  UninstallProgressForm.BeveledLabel.Visible := False;
  Card := TPanel.Create(UninstallProgressForm);
  Card.Parent := UninstallProgressForm;
  Place(Card, 20, 20, 570, 185);
  Surface(Card, CardColor);
  UninstallProgressForm.OuterNotebook.Parent := Card;
  Place(UninstallProgressForm.OuterNotebook, 0, 0, 570, 185);
  Place(UninstallProgressForm.InnerNotebook, 0, 0, 570, 185);
  LayoutBody(UninstallProgressForm.InnerPage);
  LayoutBody(UninstallProgressForm.InstallingPage);
  UninstallProgressForm.PageNameLabel.Parent := UninstallProgressForm.InstallingPage;
  Place(UninstallProgressForm.PageNameLabel, 24, 12, 522, 45);
  LabelFace(UninstallProgressForm.PageNameLabel, 24, InkColor, True);
  Place(UninstallProgressForm.StatusLabel, 24, 58, 522, 45);
  LabelFace(UninstallProgressForm.StatusLabel, 12, MutedColor, False);
  if ClearUserData then
    UninstallProgressForm.StatusLabel.Caption := CustomMessage('RemovingWithData')
  else
    UninstallProgressForm.StatusLabel.Caption :=
      FmtMessage(SetupMessage(msgUninstallStatusLabel), ['tt tool']);
  TextLabel(UninstallProgressForm.InstallingPage, ExpandConstant('{app}'),
    24, 108, 522, 40, 10, MutedColor, False);
  Place(UninstallProgressForm.ProgressBar, 24, 151, 522, 18);
  BeginReveal(UninstallProgressForm);
end;

procedure OpenStableRelease(Sender: TObject);
var
  ErrorCode: Integer;
begin
  if not ShellExec('open', 'https://github.com/Estrella-071/tt-tool/releases/latest',
    '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode) then
    MsgBox(SysErrorMessage(ErrorCode), mbError, MB_OK);
end;

function ShortcutHash(const Path: String): String;
begin
  Result := '';
  if not FileExists(Path) then
    Exit;
  try
    Result := GetSHA256OfFile(Path);
  except
    Log('A shortcut could not be identified for the removal result.');
  end;
end;

procedure RememberRemovalShortcut(const Path, SavedHash: String);
var
  Hash: String;
  Index: Integer;
begin
  Hash := ShortcutHash(Path);
  if Hash = '' then
    Exit;
  if SavedHash <> '' then begin
    if CompareText(Hash, SavedHash) <> 0 then
      Exit;
  end else if not LegacyStartMenuLink(Path) then
    Exit;
  Index := GetArrayLength(RemovalShortcuts);
  SetArrayLength(RemovalShortcuts, Index + 1);
  RemovalShortcuts[Index].Path := Path;
  RemovalShortcuts[Index].Hash := Hash;
end;

function InstalledProgramRemains: Boolean;
var
  AppDir, RuntimeDir: String;
  I: Integer;
begin
  AppDir := AddBackslash(ExpandConstant('{app}'));
  RuntimeDir := AppDir + 'runtime\';
  Result := FileExists(AppDir + 'app\tt_tool_launcher.py') or
    FileExists(AppDir + 'app\qt_fishing.py') or
    FileExists(RuntimeDir + 'python.exe') or
    FileExists(RuntimeDir + 'pythonw.exe') or
    FileExists(RuntimeDir + 'python312.dll') or
    FileExists(RuntimeDir + 'python312.zip') or
    FileExists(RuntimeDir + 'Lib\site-packages\PySide6\Qt6Core.dll') or
    FileExists(RuntimeDir + 'Lib\site-packages\PySide6\Qt6Gui.dll') or
    FileExists(RuntimeDir + 'Lib\site-packages\PySide6\Qt6Widgets.dll');
  if Result then
    Exit;
  for I := 0 to GetArrayLength(RemovalShortcuts) - 1 do
    if CompareText(ShortcutHash(RemovalShortcuts[I].Path), RemovalShortcuts[I].Hash) = 0 then begin
      Result := True;
      Exit;
    end;
end;

procedure ShowRemovalCompletion;
var
  Dialog: TSetupForm;
  Card: TPanel;
  CloseButton, ReleaseButton: TNewButton;
  Detail: String;
begin
  Dialog := CreateCustomForm(610, 230, True, True);
  try
    Dialog.Caption := 'tt tool · ' + CustomMessage('RemoveMode');
    Dialog.Position := poScreenCenter;
    Frame(Dialog, 610, 230);
    Card := TPanel.Create(Dialog);
    Card.Parent := Dialog;
    Place(Card, 20, 20, 570, 135);
    if not HighContrastActive then
      Surface(Card, CardColor);
    TextLabel(Card, CustomMessage('RemoveFinishedHeading'), 24, 14, 522, 45, 24, InkColor, True);
    if InstalledProgramRemains or not RemovalDataComplete then
      Detail := CustomMessage('RemoveFinishedPartial')
    else if ClearUserData then
      Detail := CustomMessage('RemoveFinishedCleared')
    else
      Detail := CustomMessage('RemoveFinishedKept');
    TextLabel(Card, Detail, 24, 60, 522, 60, 12, MutedColor, False);
    ReleaseButton := TNewButton.Create(Dialog);
    ReleaseButton.Parent := Dialog;
    ReleaseButton.Caption := CustomMessage('RemoveOpenReleases');
    ReleaseButton.OnClick := @OpenStableRelease;
    Place(ReleaseButton, 20, 170, 224, 44);
    CloseButton := TNewButton.Create(Dialog);
    CloseButton.Parent := Dialog;
    CloseButton.Caption := CustomMessage('RemoveClose');
    CloseButton.ModalResult := mrOk;
    CloseButton.Default := True;
    CloseButton.Cancel := True;
    Place(CloseButton, 444, 170, 146, 44);
    Dialog.ActiveControl := CloseButton;
    BeginReveal(Dialog);
    Dialog.ShowModal;
  finally
    Dialog.Free;
  end;
end;

function DataFolderIsOrdinary(const Folder: String): Boolean;
var
  Attr: Integer;
begin
  Attr := FileAttributes(Folder);
  Result := (Attr <> -1) and (Attr and (FileDirectory or FileReparsePoint) = FileDirectory);
end;

function RemoveOwnData(const Folder: String; Notice: TSetupForm; var LastPaint: Int64): Boolean;
var
  Entry: TFindRec;
  Child: String;
begin
  if not DataFolderIsOrdinary(Folder) then begin
    Result := False;
    Exit;
  end;
  Result := True;
  if FindFirst(AddBackslash(Folder) + '*', Entry) then begin
    try
      repeat
        if (Notice <> nil) and (WindowsTick - LastPaint >= 32) then begin
          PaintRemovalNotice(Notice);
          LastPaint := WindowsTick;
        end;
        if (Entry.Name <> '.') and (Entry.Name <> '..') then begin
          Child := AddBackslash(Folder) + Entry.Name;
          if Entry.Attributes and FileReparsePoint <> 0 then
            Result := False
          else if Entry.Attributes and FileDirectory <> 0 then begin
            if not RemoveOwnData(Child, Notice, LastPaint) then
              Result := False;
          end else if not DeleteFile(Child) then
            Result := False;
        end;
      until not FindNext(Entry);
    finally
      FindClose(Entry);
    end;
  end;
  if not RemoveDir(Folder) then
    Result := False;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Base, Data: String;
  Notice: TSetupForm;
  LastPaint: Int64;
  Interactive: Boolean;
begin
  Interactive := not HasUninstallSwitch('/VERYSILENT') and
    (HasUninstallSwitch('/TTTOOLPROMPT') or HasUninstallSwitch('/TTTOOLCOMPLETE'));
  if (CurUninstallStep = usUninstall) and Interactive then begin
    RememberRemovalShortcut(ExpandConstant('{app}\tt tool.lnk'), '');
    RememberRemovalShortcut(ExpandConstant('{userprograms}\tt tool\tt tool.lnk'),
      GetPreviousData(StartMenuHash, ''));
    RememberRemovalShortcut(ExpandConstant('{userdesktop}\tt tool.lnk'),
      GetPreviousData(DesktopHash, ''));
  end;
  if (CurUninstallStep = usPostUninstall) and ClearUserData then begin
    Base := ExpandConstant('{localappdata}\tt-tool');
    Data := AddBackslash(Base) + 'data';
    if DirExists(Data) then begin
      RemovalDataComplete := DataFolderIsOrdinary(Base) and DataFolderIsOrdinary(Data);
      if RemovalDataComplete then begin
        Notice := nil;
        if Interactive then
          Notice := OpenRemovalNotice(CustomMessage('RemoveDataHeading'), CustomMessage('RemoveDataDetail'));
        try
          LastPaint := 0;
          RemovalDataComplete := RemoveOwnData(Data, Notice, LastPaint);
        finally
          if Notice <> nil then begin
            Notice.Hide;
            Notice.Free;
          end;
        end;
      end;
      if not RemovalDataComplete then
        Log('Some tt tool data could not be removed.');
    end;
  end;
  if (CurUninstallStep = usDone) and Interactive then
    ShowRemovalCompletion;
end;
