// SPDX-License-Identifier: GPL-3.0-only
const
  ShellColor = $00EEE6E9;
  CardColor = $00FAF7F9;
  HeaderColor = $00402B30;
  AccentColor = $00874E5F;
  InkColor = $00402B30;
  MutedColor = $00705A62;
  FocusColor = $00AF728E;
  ButtonColor = $00EFE9EE;
  PressedColor = $006A394D;
  WmPaint = $000F;
  WmEnable = $000A;
  WmSetText = $000C;
  WmSetFocus = $0007;
  WmKillFocus = $0008;
  WmNcDestroy = $0082;
  WmWindowPosChanging = $0046;
  WmWindowPosChanged = $0047;
  WmTimer = $0113;
  WmNcLeftDown = $00A1;
  WmLeftDown = $0201;
  WmLeftUp = $0202;
  WmMouseMove = $0200;
  WmMouseLeave = $02A3;
  WmKeyDown = $0100;
  WmKeyUp = $0101;
  BmGetState = $00F2;
  BstPushed = $04;
  BstHot = $0200;
  HtCaption = 2;
  WindowCopy = $00CC0020;
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

function WindowRegion(X1, Y1, X2, Y2, EllipseWidth, EllipseHeight: Integer): NativeUInt;
  external 'CreateRoundRectRgn@gdi32.dll stdcall';
function ApplyWindowRegion(Wnd: HWND; Region: NativeUInt; Redraw: Boolean): Integer;
  external 'SetWindowRgn@user32.dll stdcall';
function DisposeGraphics(Handle: NativeUInt): Boolean;
  external 'DeleteObject@gdi32.dll stdcall';
function AddWindowSubclass(Wnd: HWND; Callback: NativeInt; Id, Data: NativeUInt): Boolean;
  external 'SetWindowSubclass@comctl32.dll stdcall';
function RemoveWindowSubclass(Wnd: HWND; Callback: NativeInt; Id: NativeUInt): Boolean;
  external 'RemoveWindowSubclass@comctl32.dll stdcall';
function ContinueWindowMessage(Wnd: HWND; Message: Cardinal; WParam: NativeUInt; LParam: NativeInt): NativeInt;
  external 'DefSubclassProc@comctl32.dll stdcall';
function WindowDC(Wnd: HWND): HDC;
  external 'GetDC@user32.dll stdcall';
function ReleaseWindowDC(Wnd: HWND; DC: HDC): Integer;
  external 'ReleaseDC@user32.dll stdcall';
function CopyButtonPixels(DC: HDC; X, Y, Width, Height: Integer; Source: HDC;
  SrcX, SrcY: Integer; Mode: Cardinal): Boolean;
  external 'BitBlt@gdi32.dll stdcall';
function RedrawWindowArea(Wnd: HWND; Region: NativeUInt; Erase: Boolean): Boolean;
  external 'InvalidateRect@user32.dll stdcall';
function ValidateWindowArea(Wnd: HWND; Region: NativeUInt): Boolean;
  external 'ValidateRect@user32.dll stdcall';
function UseHeaderDrag: Boolean;
  external 'ReleaseCapture@user32.dll stdcall';
function CursorScreenPosition(var Point: TScreenPoint): Boolean;
  external 'GetCursorPos@user32.dll stdcall';
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

type
  TStyledButton = record
    Button: TNewButton;
    WindowHandle: HWND;
    Primary: Boolean;
    Background: TColor;
  end;

var
  StyledButtons: array of TStyledButton;
  HeaderWindows: array of HWND;
  StyledButtonCallback, HeaderCallback: NativeInt;
  FadeCallback, OriginalExtendedStyle: NativeInt;
  FadingWindow: HWND;
  FadeStarted: Int64;
  CurrentAlpha: Byte;
  ClosingFade: Boolean;
  ClearUserData: Boolean;
  RemovalDataComplete: Boolean;

procedure RoundControl(Control: TWinControl; Diameter: Integer);
var
  Clip: NativeUInt;
begin
  if HighContrastActive then
    Exit;
  Clip := WindowRegion(0, 0, Control.Width + 1, Control.Height + 1,
    ScaleX(Diameter), ScaleY(Diameter));
  if (Clip <> 0) and (ApplyWindowRegion(Control.Handle, Clip, True) = 0) then
    DisposeGraphics(Clip);
end;

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
  RoundControl(Panel, 24);
end;

procedure LabelFace(LabelText: TNewStaticText; Size: Integer; Foreground: TColor; Heading: Boolean);
begin
  LabelText.AutoSize := False;
  LabelText.WordWrap := True;
  LabelText.StyleElements := [];
  LabelText.Font.Size := Size;
  LabelText.Font.Color := Foreground;
  if Heading then begin
    LabelText.Font.Name := 'Georgia';
    LabelText.Font.Style := [fsBold];
  end;
end;

procedure PaintAction(Wnd: HWND; Entry: TStyledButton);
var
  Button: TNewButton;
  Picture: TBitmap;
  Bounds: TRect;
  DC: HDC;
  State, X, Y, R: Integer;
  Fill, TextColor: TColor;
  Title: String;
begin
  Button := Entry.Button;
  DC := WindowDC(Wnd);
  if DC = 0 then
    Exit;
  Picture := TBitmap.Create;
  try
    Bounds.Left := 0;
    Bounds.Top := 0;
    Bounds.Right := Button.Width;
    Bounds.Bottom := Button.Height;
    Picture.Width := Bounds.Right;
    Picture.Height := Bounds.Bottom;
    Picture.Canvas.Brush.Color := Entry.Background;
    Picture.Canvas.FillRect(Bounds);

    State := SendMessage(Wnd, BmGetState, 0, 0);
    Fill := ButtonColor;
    TextColor := InkColor;
    if not Button.Enabled then begin
      Fill := $00E3DCE2;
      TextColor := $00867980;
    end else if Entry.Primary then begin
      Fill := AccentColor;
      TextColor := clWhite;
      if State and BstHot <> 0 then
        Fill := $00945A6B;
      if State and BstPushed <> 0 then
        Fill := PressedColor;
    end else if State and (BstHot or BstPushed) <> 0 then
      Fill := $00E1D7E7;
    Picture.Canvas.Pen.Style := psClear;
    if Button.Focused then begin
      Picture.Canvas.Pen.Style := psSolid;
      Picture.Canvas.Pen.Color := FocusColor;
      Picture.Canvas.Pen.Width := ScaleX(2);
    end;
    Picture.Canvas.Brush.Color := Fill;
    R := ScaleX(18);
    Picture.Canvas.RoundRect(1, 1, Bounds.Right - 1, Bounds.Bottom - 1, R, R);
    Title := Button.Caption;
    StringChangeEx(Title, '&', '', True);
    Picture.Canvas.Font.Assign(Button.Font);
    Picture.Canvas.Font.Color := TextColor;
    Picture.Canvas.Brush.Style := bsClear;
    X := (Bounds.Right - Picture.Canvas.TextWidth(Title)) div 2;
    Y := (Bounds.Bottom - Picture.Canvas.TextHeight(Title)) div 2;
    Picture.Canvas.TextOut(X, Y, Title);
    CopyButtonPixels(DC, 0, 0, Bounds.Right, Bounds.Bottom, Picture.Canvas.Handle, 0, 0, WindowCopy);
  finally
    Picture.Free;
    ReleaseWindowDC(Wnd, DC);
    ValidateWindowArea(Wnd, 0);
  end;
end;

function ActionWindowProc(Wnd: HWND; Message: Cardinal; WParam: NativeUInt;
  LParam: NativeInt; Id, Data: NativeUInt): NativeInt;
begin
  if Message = WmPaint then begin
    PaintAction(Wnd, StyledButtons[Integer(Data)]);
    Result := 0;
    Exit;
  end;
  if Message = WmNcDestroy then
    RemoveWindowSubclass(Wnd, StyledButtonCallback, Id);
  Result := ContinueWindowMessage(Wnd, Message, WParam, LParam);
  case Message of
    WmEnable, WmSetText, WmSetFocus, WmKillFocus, WmLeftDown, WmLeftUp,
    WmMouseMove, WmMouseLeave, WmKeyDown, WmKeyUp:
      RedrawWindowArea(Wnd, 0, False);
  end;
end;

procedure StyleAction(Button: TNewButton; Primary: Boolean; Background: TColor);
var
  Index: Integer;
begin
  if HighContrastActive then
    Exit;
  Button.Font.Size := 11;
  Button.Font.Style := [fsBold];
  Button.Cursor := crHandPoint;
  Index := GetArrayLength(StyledButtons);
  SetArrayLength(StyledButtons, Index + 1);
  StyledButtons[Index].Button := Button;
  StyledButtons[Index].WindowHandle := Button.Handle;
  StyledButtons[Index].Primary := Primary;
  StyledButtons[Index].Background := Background;
  if StyledButtonCallback = 0 then
    StyledButtonCallback := CreateCallback(@ActionWindowProc);
  AddWindowSubclass(StyledButtons[Index].WindowHandle, StyledButtonCallback, 1, Index);
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

procedure CompleteReveal(Wnd: HWND);
begin
  StopWindowTimer(Wnd, FadeTimer);
  CurrentAlpha := 255;
  WindowOpacity(Wnd, 0, CurrentAlpha, AlphaEffect);
  WriteWindowStyle(Wnd, ExtendedStyleIndex, OriginalExtendedStyle);
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

function HeaderWindowProc(Wnd: HWND; Message: Cardinal; WParam: NativeUInt;
  LParam: NativeInt; Id, Data: NativeUInt): NativeInt;
var
  Point: TScreenPoint;
begin
  if (Message = WmLeftDown) and CursorScreenPosition(Point) then begin
    UseHeaderDrag;
    Result := SendMessage(HWND(Data), WmNcLeftDown, HtCaption,
      ((Point.Y and $FFFF) shl 16) or (Point.X and $FFFF));
  end else begin
    if Message = WmNcDestroy then
      RemoveWindowSubclass(Wnd, HeaderCallback, Id);
    Result := ContinueWindowMessage(Wnd, Message, WParam, LParam);
  end;
end;

procedure AddHeaderDrag(Control: TWinControl; Window: TForm);
var
  Index: Integer;
  WindowHandle: HWND;
begin
  if HeaderCallback = 0 then
    HeaderCallback := CreateCallback(@HeaderWindowProc);
  WindowHandle := Control.Handle;
  if AddWindowSubclass(WindowHandle, HeaderCallback, 2, Window.Handle) then begin
    Index := GetArrayLength(HeaderWindows);
    SetArrayLength(HeaderWindows, Index + 1);
    HeaderWindows[Index] := WindowHandle;
  end;
end;

procedure RemoveActiveSubclasses;
var
  I: Integer;
begin
  if FadingWindow <> 0 then begin
    CompleteReveal(FadingWindow);
    RemoveWindowSubclass(FadingWindow, FadeCallback, 3);
  end;
  for I := 0 to GetArrayLength(StyledButtons) - 1 do
    RemoveWindowSubclass(StyledButtons[I].WindowHandle, StyledButtonCallback, 1);
  for I := 0 to GetArrayLength(HeaderWindows) - 1 do
    RemoveWindowSubclass(HeaderWindows[I], HeaderCallback, 2);
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

procedure LayoutHeader(Parent: TWinControl; Window: TForm; Width: Integer; Subtitle: String);
var
  Header: TPanel;
  Brand, Role: TNewStaticText;
begin
  Header := TPanel.Create(Parent);
  Header.Parent := Parent;
  Place(Header, 20, 17, Width - 40, 68);
  if not HighContrastActive then
    Surface(Header, HeaderColor);
  Brand := TextLabel(Header, 'tt tool', 24, 9, 170, 48, 27, clWhite, True);
  Role := TextLabel(Header, Subtitle, 191, 24, Width - 255, 34, 12, $00E5DBEA, False);
  if not HighContrastActive then begin
    AddHeaderDrag(Header, Window);
    AddHeaderDrag(Brand, Window);
    AddHeaderDrag(Role, Window);
  end;
end;

procedure Frame(Window: TForm; Width, Height: Integer);
begin
  if HighContrastActive then
    Exit;
  Window.StyleElements := [];
  Window.BorderStyle := bsNone;
  Window.Position := poScreenCenter;
  Window.ClientWidth := ScaleX(Width);
  Window.ClientHeight := ScaleY(Height);
  Window.Color := ShellColor;
  RoundControl(Window, 28);
end;

procedure LayoutBody(Body: TNewNotebookPage);
begin
  Body.StyleElements := [];
  Body.ParentBackground := False;
  Body.Color := CardColor;
end;

procedure LayoutLicenseControls;
begin
  { The notebook aligns an inactive page when it is made visible. Do not carry
    its original bottom anchors over to the new fixed-height content layout. }
  WizardForm.LicenseLabel1.Anchors := [akLeft, akTop];
  WizardForm.LicenseMemo.Anchors := [akLeft, akTop];
  WizardForm.LicenseAcceptedRadio.Anchors := [akLeft, akTop];
  WizardForm.LicenseNotAcceptedRadio.Anchors := [akLeft, akTop];
  Place(WizardForm.LicenseLabel1, 0, 0, 608, 25);
  Place(WizardForm.LicenseMemo, 0, 27, 608, 166);
  Place(WizardForm.LicenseAcceptedRadio, 0, 197, 608, 27);
  Place(WizardForm.LicenseNotAcceptedRadio, 0, 226, 608, 27);
end;

procedure InitializeWizard;
var
  I: Integer;
  Card: TPanel;
begin
  if WizardSilent or HighContrastActive then
    Exit;
  Frame(WizardForm, 704, 540);
  LayoutHeader(WizardForm, WizardForm, 704, CustomMessage('InstallMode'));
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
  WizardForm.MainPanel.Visible := False;
  WizardForm.WizardBitmapImage.Visible := False;
  WizardForm.WizardBitmapImage2.Visible := False;
  WizardForm.SelectDirBitmapImage.Visible := False;

  Card := TPanel.Create(WizardForm);
  Card.Parent := WizardForm;
  Place(Card, 20, 101, 664, 361);
  Surface(Card, CardColor);

  WizardForm.OuterNotebook.Parent := Card;
  WizardForm.OuterNotebook.Anchors := [akLeft, akTop];
  Place(WizardForm.OuterNotebook, 0, 0, 664, 361);
  for I := 0 to WizardForm.OuterNotebook.PageCount - 1 do
    LayoutBody(WizardForm.OuterNotebook.Pages[I]);
  for I := 0 to WizardForm.InnerNotebook.PageCount - 1 do
    LayoutBody(WizardForm.InnerNotebook.Pages[I]);
  WizardForm.InnerNotebook.Anchors := [akLeft, akTop];
  Place(WizardForm.InnerNotebook, 28, 92, 608, 254);

  WizardForm.PageNameLabel.Parent := WizardForm.InnerPage;
  Place(WizardForm.PageNameLabel, 28, 14, 608, 45);
  LabelFace(WizardForm.PageNameLabel, 24, InkColor, True);
  WizardForm.PageDescriptionLabel.Parent := WizardForm.InnerPage;
  Place(WizardForm.PageDescriptionLabel, 28, 58, 608, 32);
  LabelFace(WizardForm.PageDescriptionLabel, 12, MutedColor, False);

  Place(WizardForm.WelcomeLabel1, 28, 59, 608, 73);
  LabelFace(WizardForm.WelcomeLabel1, 33, InkColor, True);
  Place(WizardForm.WelcomeLabel2, 28, 143, 578, 155);
  LabelFace(WizardForm.WelcomeLabel2, 15, MutedColor, False);
  Place(WizardForm.FinishedHeadingLabel, 28, 50, 608, 62);
  LabelFace(WizardForm.FinishedHeadingLabel, 30, InkColor, True);
  Place(WizardForm.FinishedLabel, 28, 119, 608, 94);
  LabelFace(WizardForm.FinishedLabel, 14, MutedColor, False);
  Place(WizardForm.RunList, 28, 221, 608, 95);
  Place(WizardForm.YesRadio, 28, 221, 608, 34);
  Place(WizardForm.NoRadio, 28, 259, 608, 34);

  LabelFace(WizardForm.LicenseLabel1, 11, InkColor, False);
  WizardForm.LicenseMemo.Color := clWhite;
  WizardForm.LicenseMemo.BorderStyle := bsSingle;
  WizardForm.LicenseMemo.ScrollBars := ssVertical;
  WizardForm.LicenseMemo.Font.Name := 'Segoe UI';
  WizardForm.LicenseMemo.Font.Size := 11;
  WizardForm.LicenseMemo.TabStop := True;
  WizardForm.LicenseAcceptedRadio.Font.Size := 11;
  WizardForm.LicenseNotAcceptedRadio.Font.Size := 11;
  LayoutLicenseControls;

  Place(WizardForm.SelectDirLabel, 0, 9, 608, 42);
  LabelFace(WizardForm.SelectDirLabel, 12, InkColor, False);
  Place(WizardForm.SelectDirBrowseLabel, 0, 59, 608, 32);
  LabelFace(WizardForm.SelectDirBrowseLabel, 11, MutedColor, False);
  WizardForm.DirEdit.AutoSize := False;
  WizardForm.DirEdit.Font.Size := 12;
  Place(WizardForm.DirEdit, 0, 98, 448, 37);
  Place(WizardForm.DirBrowseButton, 464, 95, 144, 44);
  Place(WizardForm.DiskSpaceLabel, 0, 162, 608, 28);
  LabelFace(WizardForm.DiskSpaceLabel, 11, MutedColor, False);
  StyleAction(WizardForm.DirBrowseButton, False, CardColor);

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

  Place(WizardForm.CancelButton, 20, 479, 142, 46);
  Place(WizardForm.BackButton, 378, 479, 146, 46);
  Place(WizardForm.NextButton, 538, 479, 146, 46);
  StyleAction(WizardForm.CancelButton, False, ShellColor);
  StyleAction(WizardForm.BackButton, False, ShellColor);
  StyleAction(WizardForm.NextButton, True, ShellColor);
  BeginReveal(WizardForm);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpLicense) and not WizardSilent then begin
    if not HighContrastActive then
      LayoutLicenseControls;
    if WizardForm.LicenseMemo.CanFocus then
      WizardForm.ActiveControl := WizardForm.LicenseMemo;
  end;
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
  Dialog := CreateCustomForm(610, 397, True, True);
  try
    Dialog.Caption := CustomMessage('RemoveHeading');
    Dialog.Position := poScreenCenter;
    Frame(Dialog, 610, 397);
    LayoutHeader(Dialog, Dialog, 610, CustomMessage('RemoveMode'));
    Card := TPanel.Create(Dialog);
    Card.Parent := Dialog;
    Place(Card, 20, 101, 570, 222);
    if not HighContrastActive then
      Surface(Card, CardColor);
    TextLabel(Card, CustomMessage('RemoveHeading'), 24, 12, 522, 47, 24, InkColor, True);
    TextLabel(Card, CustomMessage('RemoveDescription'), 24, 60, 522, 46, 12, MutedColor, False);
    TextLabel(Card, CustomMessage('RemoveFolderLabel'), 24, 111, 522, 23, 10, MutedColor, False);
    Directory := TNewEdit.Create(Card);
    Directory.Parent := Card;
    Directory.ReadOnly := True;
    Directory.AutoSize := False;
    Directory.Font.Size := 11;
    Directory.Text := ExpandConstant('{app}');
    Place(Directory, 24, 136, 522, 33);
    Toggle := TNewCheckBox.Create(Card);
    Toggle.Parent := Card;
    Toggle.Caption := CustomMessage('RemoveDataOption');
    Toggle.Checked := False;
    Toggle.Font.Size := 11;
    Place(Toggle, 24, 177, 522, 32);
    Cancel := TNewButton.Create(Dialog);
    Cancel.Parent := Dialog;
    Cancel.Caption := SetupMessage(msgButtonCancel);
    Cancel.ModalResult := mrCancel;
    Cancel.Cancel := True;
    Cancel.Default := True;
    Place(Cancel, 20, 338, 142, 44);
    StyleAction(Cancel, False, ShellColor);
    Remove := TNewButton.Create(Dialog);
    Remove.Parent := Dialog;
    Remove.Caption := CustomMessage('RemoveAction');
    Remove.ModalResult := mrOk;
    Place(Remove, 424, 338, 166, 44);
    StyleAction(Remove, True, ShellColor);
    Dialog.ActiveControl := Cancel;
    BeginReveal(Dialog);
    Result := Dialog.ShowModal = mrOk;
    ClearUserData := Result and Toggle.Checked;
  finally
    Dialog.Free;
  end;
end;

procedure WaitForApplicationExit(Timeout: Cardinal);
var
  Deadline: Int64;
begin
  Deadline := WindowsTick + Int64(Timeout);
  while CheckForMutexes(AppRunningMutex) and (WindowsTick < Deadline) do
    Sleep(50);
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
  Frame(UninstallProgressForm, 610, 307);
  LayoutHeader(UninstallProgressForm, UninstallProgressForm, 610, CustomMessage('RemoveMode'));
  UninstallProgressForm.Bevel.Visible := False;
  UninstallProgressForm.Bevel1.Visible := False;
  UninstallProgressForm.MainPanel.Visible := False;
  UninstallProgressForm.BeveledLabel.Visible := False;
  Card := TPanel.Create(UninstallProgressForm);
  Card.Parent := UninstallProgressForm;
  Place(Card, 20, 101, 570, 185);
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

procedure ShowRemovalCompletion;
var
  Dialog: TSetupForm;
  Card: TPanel;
  CloseButton, ReleaseButton: TNewButton;
  Detail: String;
begin
  Dialog := CreateCustomForm(610, 311, True, True);
  try
    Dialog.Caption := CustomMessage('RemoveFinishedHeading');
    Dialog.Position := poScreenCenter;
    Frame(Dialog, 610, 311);
    LayoutHeader(Dialog, Dialog, 610, CustomMessage('RemoveMode'));
    Card := TPanel.Create(Dialog);
    Card.Parent := Dialog;
    Place(Card, 20, 101, 570, 135);
    if not HighContrastActive then
      Surface(Card, CardColor);
    TextLabel(Card, CustomMessage('RemoveFinishedHeading'), 24, 14, 522, 45, 24, InkColor, True);
    if FileExists(ExpandConstant('{app}\app\tt_tool_launcher.py')) or not RemovalDataComplete then
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
    Place(ReleaseButton, 20, 251, 224, 44);
    StyleAction(ReleaseButton, False, ShellColor);
    CloseButton := TNewButton.Create(Dialog);
    CloseButton.Parent := Dialog;
    CloseButton.Caption := CustomMessage('RemoveClose');
    CloseButton.ModalResult := mrOk;
    CloseButton.Default := True;
    CloseButton.Cancel := True;
    Place(CloseButton, 444, 251, 146, 44);
    StyleAction(CloseButton, True, ShellColor);
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

function RemoveOwnData(const Folder: String): Boolean;
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
        if (Entry.Name <> '.') and (Entry.Name <> '..') then begin
          Child := AddBackslash(Folder) + Entry.Name;
          if Entry.Attributes and FileReparsePoint <> 0 then
            Result := False
          else if Entry.Attributes and FileDirectory <> 0 then begin
            if not RemoveOwnData(Child) then
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
begin
  if (CurUninstallStep = usPostUninstall) and ClearUserData then begin
    Base := ExpandConstant('{localappdata}\tt-tool');
    Data := AddBackslash(Base) + 'data';
    if DirExists(Data) then begin
      RemovalDataComplete := DataFolderIsOrdinary(Base) and DataFolderIsOrdinary(Data);
      if RemovalDataComplete then
        RemovalDataComplete := RemoveOwnData(Data);
      if not RemovalDataComplete then
        Log('Some tt tool data could not be removed.');
    end;
  end;
  if (CurUninstallStep = usDone) and not HasUninstallSwitch('/VERYSILENT') and
    (HasUninstallSwitch('/TTTOOLPROMPT') or HasUninstallSwitch('/TTTOOLCOMPLETE')) then
    ShowRemovalCompletion;
end;
