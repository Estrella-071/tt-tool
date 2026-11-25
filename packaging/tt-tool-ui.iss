; SPDX-License-Identifier: GPL-3.0-only
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
  ClearUserData: Boolean;

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
  Control.Anchors := [akLeft, akTop];
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
  Button.Font.Size := 10;
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
  Brand := TextLabel(Header, 'tt tool', 22, 14, 160, 37, 24, clWhite, True);
  Role := TextLabel(Header, Subtitle, 185, 25, Width - 251, 30, 11, $00E5DBEA, False);
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

procedure InitializeWizard;
var
  I: Integer;
  Card: TPanel;
begin
  if WizardSilent or HighContrastActive then
    Exit;
  Frame(WizardForm, 620, 429);
  LayoutHeader(WizardForm, WizardForm, 620, CustomMessage('InstallMode'));
  WizardForm.Bevel.Visible := False;
  WizardForm.Bevel1.Visible := False;
  WizardForm.MainPanel.Visible := False;
  WizardForm.WizardBitmapImage.Visible := False;
  WizardForm.WizardBitmapImage2.Visible := False;
  WizardForm.SelectDirBitmapImage.Visible := False;

  Card := TPanel.Create(WizardForm);
  Card.Parent := WizardForm;
  Place(Card, 20, 97, 580, 263);
  Surface(Card, CardColor);

  WizardForm.OuterNotebook.Parent := Card;
  Place(WizardForm.OuterNotebook, 0, 0, 580, 263);
  for I := 0 to WizardForm.OuterNotebook.PageCount - 1 do
    LayoutBody(WizardForm.OuterNotebook.Pages[I]);
  for I := 0 to WizardForm.InnerNotebook.PageCount - 1 do
    LayoutBody(WizardForm.InnerNotebook.Pages[I]);
  Place(WizardForm.InnerNotebook, 26, 78, 528, 170);

  WizardForm.PageNameLabel.Parent := WizardForm.InnerPage;
  Place(WizardForm.PageNameLabel, 26, 13, 528, 38);
  LabelFace(WizardForm.PageNameLabel, 21, InkColor, True);
  WizardForm.PageDescriptionLabel.Parent := WizardForm.InnerPage;
  Place(WizardForm.PageDescriptionLabel, 26, 51, 528, 28);
  LabelFace(WizardForm.PageDescriptionLabel, 10, MutedColor, False);

  Place(WizardForm.WelcomeLabel1, 26, 47, 528, 61);
  LabelFace(WizardForm.WelcomeLabel1, 29, InkColor, True);
  Place(WizardForm.WelcomeLabel2, 26, 119, 528, 115);
  LabelFace(WizardForm.WelcomeLabel2, 13, MutedColor, False);
  Place(WizardForm.FinishedHeadingLabel, 26, 43, 528, 55);
  LabelFace(WizardForm.FinishedHeadingLabel, 26, InkColor, True);
  Place(WizardForm.FinishedLabel, 26, 105, 528, 66);
  LabelFace(WizardForm.FinishedLabel, 12, MutedColor, False);
  Place(WizardForm.RunList, 26, 178, 528, 70);
  Place(WizardForm.YesRadio, 26, 177, 528, 27);
  Place(WizardForm.NoRadio, 26, 207, 528, 27);

  Place(WizardForm.LicenseLabel1, 0, 4, 528, 23);
  Place(WizardForm.LicenseMemo, 0, 28, 528, 87);
  Place(WizardForm.LicenseAcceptedRadio, 0, 117, 528, 23);
  Place(WizardForm.LicenseNotAcceptedRadio, 0, 142, 528, 23);

  Place(WizardForm.SelectDirLabel, 0, 6, 528, 34);
  Place(WizardForm.SelectDirBrowseLabel, 0, 50, 528, 29);
  WizardForm.DirEdit.AutoSize := False;
  Place(WizardForm.DirEdit, 0, 85, 386, 33);
  Place(WizardForm.DirBrowseButton, 398, 83, 130, 38);
  Place(WizardForm.DiskSpaceLabel, 0, 142, 528, 23);
  StyleAction(WizardForm.DirBrowseButton, False, CardColor);

  Place(WizardForm.SelectTasksLabel, 0, 7, 528, 45);
  Place(WizardForm.TasksList, 0, 54, 528, 112);
  WizardForm.TasksList.MinItemHeight := ScaleY(32);
  WizardForm.TasksList.BorderStyle := bsNone;
  WizardForm.TasksList.Color := CardColor;
  Place(WizardForm.ReadyLabel, 0, 4, 528, 36);
  Place(WizardForm.ReadyMemo, 0, 40, 528, 119);
  Place(WizardForm.StatusLabel, 0, 21, 528, 26);
  Place(WizardForm.ProgressGauge, 0, 54, 528, 19);
  Place(WizardForm.FilenameLabel, 0, 81, 528, 39);
  Place(WizardForm.PreparingErrorBitmapImage, 0, 8, 32, 32);
  Place(WizardForm.PreparingLabel, 46, 8, 482, 68);
  Place(WizardForm.PreparingMemo, 0, 79, 528, 80);
  Place(WizardForm.PreparingYesRadio, 46, 99, 482, 25);
  Place(WizardForm.PreparingNoRadio, 46, 130, 482, 25);

  Place(WizardForm.CancelButton, 20, 374, 125, 40);
  Place(WizardForm.BackButton, 331, 374, 125, 40);
  Place(WizardForm.NextButton, 468, 374, 132, 40);
  StyleAction(WizardForm.CancelButton, False, ShellColor);
  StyleAction(WizardForm.BackButton, False, ShellColor);
  StyleAction(WizardForm.NextButton, True, ShellColor);
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
  Toggle: TNewCheckBox;
  Cancel, Remove: TNewButton;
begin
  Dialog := CreateCustomForm(562, 320, True, True);
  try
    Dialog.Caption := CustomMessage('RemoveHeading');
    Dialog.Position := poScreenCenter;
    Frame(Dialog, 562, 320);
    LayoutHeader(Dialog, Dialog, 562, CustomMessage('RemoveMode'));
    Card := TPanel.Create(Dialog);
    Card.Parent := Dialog;
    Place(Card, 20, 97, 522, 154);
    if not HighContrastActive then
      Surface(Card, CardColor);
    TextLabel(Card, CustomMessage('RemoveHeading'), 23, 12, 470, 44, 22, InkColor, True);
    TextLabel(Card, CustomMessage('RemoveDescription'), 23, 58, 470, 46, 11, MutedColor, False);
    Toggle := TNewCheckBox.Create(Card);
    Toggle.Parent := Card;
    Toggle.Caption := CustomMessage('RemoveDataOption');
    Toggle.Checked := False;
    Toggle.Font.Size := 10;
    Toggle.TabOrder := 0;
    Place(Toggle, 23, 112, 470, 29);
    Cancel := TNewButton.Create(Dialog);
    Cancel.Parent := Dialog;
    Cancel.Caption := SetupMessage(msgButtonCancel);
    Cancel.ModalResult := mrCancel;
    Cancel.Cancel := True;
    Cancel.Default := True;
    Place(Cancel, 20, 264, 132, 40);
    StyleAction(Cancel, False, ShellColor);
    Remove := TNewButton.Create(Dialog);
    Remove.Parent := Dialog;
    Remove.Caption := CustomMessage('RemoveAction');
    Remove.ModalResult := mrOk;
    Place(Remove, 390, 264, 152, 40);
    StyleAction(Remove, True, ShellColor);
    Dialog.ActiveControl := Cancel;
    Result := Dialog.ShowModal = mrOk;
    ClearUserData := Result and Toggle.Checked;
  finally
    Dialog.Free;
  end;
end;

function InitializeUninstall: Boolean;
begin
  ClearUserData := HasUninstallSwitch('/TTTOOLCLEARDATA');
  if HasUninstallSwitch('/TTTOOLPROMPT') and not HasUninstallSwitch('/VERYSILENT') then
    Result := ConfirmRemoval
  else
    Result := True;
end;

procedure InitializeUninstallProgressForm;
var
  Card: TPanel;
begin
  if HighContrastActive or HasUninstallSwitch('/VERYSILENT') then
    Exit;
  Frame(UninstallProgressForm, 562, 256);
  LayoutHeader(UninstallProgressForm, UninstallProgressForm, 562, CustomMessage('RemoveMode'));
  UninstallProgressForm.Bevel.Visible := False;
  UninstallProgressForm.Bevel1.Visible := False;
  UninstallProgressForm.MainPanel.Visible := False;
  UninstallProgressForm.BeveledLabel.Visible := False;
  Card := TPanel.Create(UninstallProgressForm);
  Card.Parent := UninstallProgressForm;
  Place(Card, 20, 97, 522, 140);
  Surface(Card, CardColor);
  UninstallProgressForm.OuterNotebook.Parent := Card;
  Place(UninstallProgressForm.OuterNotebook, 0, 0, 522, 140);
  Place(UninstallProgressForm.InnerNotebook, 0, 0, 522, 140);
  LayoutBody(UninstallProgressForm.InnerPage);
  LayoutBody(UninstallProgressForm.InstallingPage);
  UninstallProgressForm.PageNameLabel.Parent := UninstallProgressForm.InstallingPage;
  Place(UninstallProgressForm.PageNameLabel, 23, 11, 476, 42);
  LabelFace(UninstallProgressForm.PageNameLabel, 22, InkColor, True);
  Place(UninstallProgressForm.StatusLabel, 23, 54, 476, 46);
  LabelFace(UninstallProgressForm.StatusLabel, 10, MutedColor, False);
  if ClearUserData then
    UninstallProgressForm.StatusLabel.Caption := CustomMessage('RemovingWithData')
  else
    UninstallProgressForm.StatusLabel.Caption :=
      FmtMessage(SetupMessage(msgUninstallStatusLabel), ['tt tool']);
  Place(UninstallProgressForm.ProgressBar, 23, 106, 476, 18);
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
  if (CurUninstallStep <> usPostUninstall) or not ClearUserData then
    Exit;
  Base := ExpandConstant('{localappdata}\tt-tool');
  Data := AddBackslash(Base) + 'data';
  if DirExists(Data) then begin
    if not DataFolderIsOrdinary(Base) or not DataFolderIsOrdinary(Data) then
      Log('Skipped user data because its directory is a reparse point.')
    else if not RemoveOwnData(Data) then
      Log('Some tt tool data could not be removed.');
  end;
end;
