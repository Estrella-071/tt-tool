# SPDX-License-Identifier: GPL-3.0-only
# Intended for a disposable Windows x64 GitHub Actions runner.
param([Parameter(Mandatory)] [string] $SetupPath)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run this install/uninstall test on the disposable Windows runner' }

function Invoke-Setup([string] $Application, [string[]] $Flags, [int] $ExpectedExit = 0) {
    $process = Start-Process -FilePath $Application -ArgumentList $Flags -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne $ExpectedExit) {
        throw "$Application exited with $($process.ExitCode); expected $ExpectedExit"
    }
}

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class SetupWindowShape {
    private delegate bool EnumWindow(IntPtr window, IntPtr data);
    [StructLayout(LayoutKind.Sequential)]
    private struct Rect { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    private struct ScrollInfo {
        public uint Size, Mask;
        public int Min, Max;
        public uint Page;
        public int Position, TrackPosition;
    }
    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateRectRgn(int left, int top, int right, int bottom);
    [DllImport("gdi32.dll")]
    private static extern bool DeleteObject(IntPtr region);
    [DllImport("user32.dll")]
    private static extern int GetWindowRgn(IntPtr window, IntPtr region);
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindow callback, IntPtr data);
    [DllImport("user32.dll")]
    private static extern bool EnumChildWindows(IntPtr window, EnumWindow callback, IntPtr data);
    [DllImport("user32.dll")]
    private static extern int GetWindowThreadProcessId(IntPtr window, out int processId);
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")]
    public static extern bool IsWindowEnabled(IntPtr window);
    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(IntPtr window, out Rect bounds);
    [DllImport("user32.dll")]
    private static extern bool GetScrollInfo(IntPtr window, int bar, ref ScrollInfo info);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(IntPtr window, StringBuilder name, int length);
    [DllImport("user32.dll")]
    private static extern IntPtr GetParent(IntPtr window);
    [DllImport("user32.dll")]
    private static extern int GetDlgCtrlID(IntPtr window);
    [DllImport("user32.dll", EntryPoint = "PostMessageW")]
    private static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll", EntryPoint = "SendMessageTimeoutW")]
    private static extern IntPtr Query(IntPtr window, uint message, IntPtr wParam, IntPtr lParam,
        uint flags, uint timeout, out IntPtr value);
    [DllImport("user32.dll", EntryPoint = "SendMessageTimeoutW", CharSet = CharSet.Unicode)]
    private static extern IntPtr QueryText(IntPtr window, uint message, IntPtr wParam, StringBuilder buffer,
        uint flags, uint timeout, out IntPtr value);

    public static bool IsRounded(IntPtr window) {
        var region = CreateRectRgn(0, 0, 0, 0);
        try { return GetWindowRgn(window, region) == 3; }
        finally { DeleteObject(region); }
    }

    public static IntPtr[] VisibleWindows(int processId) {
        var windows = new List<IntPtr>();
        EnumWindows((window, unused) => {
            GetWindowThreadProcessId(window, out int owner);
            if (owner == processId && IsWindowVisible(window)) windows.Add(window);
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }

    public static IntPtr[] VisibleChildren(IntPtr parent) {
        var windows = new List<IntPtr>();
        EnumChildWindows(parent, (window, unused) => {
            if (IsWindowVisible(window)) windows.Add(window);
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }

    public static string ClassName(IntPtr window) {
        var text = new StringBuilder(128);
        GetClassName(window, text, text.Capacity);
        return text.ToString();
    }

    public static string Text(IntPtr window) {
        var text = new StringBuilder(8192);
        QueryText(window, 0x000D, new IntPtr(text.Capacity), text, 2, 500, out _);
        return text.ToString();
    }

    public static int Height(IntPtr window) {
        return GetWindowRect(window, out Rect bounds) ? bounds.Bottom - bounds.Top : 0;
    }

    private static int Count(IntPtr window, uint message) {
        return Query(window, message, IntPtr.Zero, IntPtr.Zero, 2, 500, out IntPtr value) == IntPtr.Zero
            ? -1 : value.ToInt32();
    }

    public static int TextLength(IntPtr window) { return Count(window, 0x000E); }
    public static int LineCount(IntPtr window) { return Count(window, 0x00BA); }

    public static bool CanScrollVertically(IntPtr window) {
        var info = new ScrollInfo { Size = (uint)Marshal.SizeOf<ScrollInfo>(), Mask = 3 };
        if (GetScrollInfo(window, 1, ref info) && info.Page > 0 && (long)info.Max - info.Min + 1 > info.Page)
            return true;
        // VCL styling can draw the scrollbar itself. Check the live viewport in that case.
        int before = Count(window, 0x00CE);
        if (before < 0) return false;
        Query(window, 0x00B6, IntPtr.Zero, new IntPtr(1), 2, 500, out _);
        int after = Count(window, 0x00CE);
        if (after <= before) return false;
        Query(window, 0x00B6, IntPtr.Zero, new IntPtr(before - after), 2, 500, out _);
        return true;
    }

    public static string[] ComboChoices(IntPtr window) {
        Query(window, 0x0146, IntPtr.Zero, IntPtr.Zero, 2, 500, out IntPtr count);
        if (count.ToInt32() != 4) return new string[0];
        var items = new string[4];
        for (int i = 0; i < items.Length; i++) {
            var text = new StringBuilder(128);
            QueryText(window, 0x0148, new IntPtr(i), text, 2, 500, out _);
            items[i] = text.ToString();
        }
        return items;
    }

    public static void SelectComboIndex(IntPtr window, int index) {
        Query(window, 0x014E, new IntPtr(index), IntPtr.Zero, 2, 500, out _);
        if (Query(window, 0x0147, IntPtr.Zero, IntPtr.Zero, 2, 500, out IntPtr selected) == IntPtr.Zero ||
            selected.ToInt32() != index)
            throw new InvalidOperationException("The language chooser did not select English");
    }

    public static void Click(IntPtr button) {
        if (!IsWindowEnabled(button))
            throw new InvalidOperationException("Cannot invoke a disabled installer control");
        // Deliver the button's BN_CLICKED to its VCL parent. BM_CLICK depends on the
        // target dialog being active, which is unreliable on a Windows runner.
        IntPtr parent = GetParent(button);
        IntPtr command = new IntPtr(GetDlgCtrlID(button) & 0xffff);
        if (parent == IntPtr.Zero || !PostMessage(parent, 0x0111, command, button))
            throw new InvalidOperationException("Could not deliver the installer button notification");
    }
}
'@

$licenseViewerClass = '^(?:TRichEditViewer(?:/Text)?|RICHEDIT(?:20W|50W))$'
$sourceLicense = Get-Content -Raw -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'LICENSE')
if ($sourceLicense -notmatch 'GNU GENERAL PUBLIC LICENSE\s+Version 3' -or $sourceLicense.Length -lt 30000) {
    throw 'The packaged source license must be the complete GNU GPL version 3'
}
$minimumLicenseText = [int](0.9 * ($sourceLicense -replace '\r', '').Length)
$minimumLicenseLines = [int](0.8 * ($sourceLicense -split '\r?\n').Count)

function Find-ChildByCaption([IntPtr] $Window, [string] $Caption, [switch] $Pattern) {
    foreach ($child in [SetupWindowShape]::VisibleChildren($Window)) {
        $label = ([SetupWindowShape]::Text($child) -replace '[\p{Cf}&]', '').Trim()
        if (($Pattern -and $label -match $Caption) -or (!$Pattern -and $label -eq $Caption)) { return $child }
    }
    return [IntPtr]::Zero
}

function Write-ProbeWindows([Collections.Generic.HashSet[int]] $TestIds) {
    foreach ($testId in @($TestIds)) {
        $windows = [SetupWindowShape]::VisibleWindows($testId)
        $candidate = Get-Process -Id $testId -ErrorAction SilentlyContinue
        Write-Host "Probe process ${testId}: running=$([bool]$candidate), windows=$($windows.Length)"
        foreach ($handle in $windows) {
            $windowClass = [SetupWindowShape]::ClassName($handle)
            $caption = [SetupWindowShape]::Text($handle)
            $rounded = [SetupWindowShape]::IsRounded($handle)
            Write-Host "  $windowClass caption=[$caption] rounded=$rounded height=$([SetupWindowShape]::Height($handle))"
            foreach ($child in [SetupWindowShape]::VisibleChildren($handle)) {
                $childClass = [SetupWindowShape]::ClassName($child)
                if ($childClass -match 'RichEdit|Memo|Edit') {
                    Write-Host "    $childClass height=$([SetupWindowShape]::Height($child)) textLength=$([SetupWindowShape]::TextLength($child)) lines=$([SetupWindowShape]::LineCount($child)) scrollable=$([SetupWindowShape]::CanScrollVertically($child))"
                }
                if ($childClass -notmatch 'Button|Radio|Static|Label') { continue }
                $childText = [SetupWindowShape]::Text($child) -replace '\s+', ' '
                if ($childText.Length -gt 240) { $childText = $childText.Substring(0, 240) }
                Write-Host "    $childClass [$childText] enabled=$([SetupWindowShape]::IsWindowEnabled($child))"
            }
        }
    }
}

function Test-RoundedWindow([string] $Application, [string[]] $Flags, [string] $WindowKind,
    [switch] $ExerciseSetup, [switch] $ExerciseRemoval) {
    $probeLog = Join-Path $env:RUNNER_TEMP "tt-tool-interactive-$($WindowKind -replace ' ', '-').log"
    $Flags += ('/LOG="' + $probeLog + '"')
    $process = Start-Process -FilePath $Application -ArgumentList $Flags -WindowStyle Normal -PassThru
    $testIds = [Collections.Generic.HashSet[int]]::new()
    $null = $testIds.Add($process.Id)
    $step = 0
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(25)
        do {
            foreach ($pidToCheck in @($testIds)) {
                foreach ($child in Get-CimInstance Win32_Process -Filter "ParentProcessId=$pidToCheck") {
                    $null = $testIds.Add([int] $child.ProcessId)
                }
            }
            foreach ($id in @($testIds)) {
                foreach ($handle in [SetupWindowShape]::VisibleWindows($id)) {
                    if ($ExerciseRemoval) {
                        $releases = Find-ChildByCaption $handle 'Open the latest stable release'
                        $close = Find-ChildByCaption $handle 'Close'
                        if ($releases -ne [IntPtr]::Zero -and $close -ne [IntPtr]::Zero) {
                            if (![SetupWindowShape]::IsRounded($handle)) {
                                throw 'Uninstall completion is missing its styled window'
                            }
                            [SetupWindowShape]::Click($close)
                            if (!$process.WaitForExit(10000) -or $process.ExitCode -ne 0) {
                                throw 'Uninstall did not finish cleanly after the completion dialog'
                            }
                            Write-Host 'Verified the uninstall completion window offers the release page'
                            return
                        }
                        continue
                    }
                    if (!$ExerciseSetup) {
                        if ([SetupWindowShape]::IsRounded($handle)) {
                            Write-Host "Observed rounded $WindowKind window ($([SetupWindowShape]::Text($handle)))."
                            return
                        }
                        continue
                    }
                    if ($step -eq 0 -and [SetupWindowShape]::ClassName($handle) -eq 'TSelectLanguageForm') {
                        $combo = [SetupWindowShape]::VisibleChildren($handle) |
                            Where-Object { [SetupWindowShape]::ClassName($_) -like '*ComboBox*' } | Select-Object -First 1
                        if (!$combo) { continue }
                        $choices = [SetupWindowShape]::ComboChoices($combo)
                        if (@(Compare-Object @('English', '繁體中文', '日本語', '한국어') $choices).Count) {
                            throw "Language chooser options unexpected: [$($choices -join ', ')]"
                        }
                        $ok = Find-ChildByCaption $handle 'OK'
                        if ($ok -eq [IntPtr]::Zero) { throw 'Language chooser has no OK control' }
                        [SetupWindowShape]::SelectComboIndex($combo, [Array]::IndexOf($choices, 'English'))
                        [SetupWindowShape]::Click($ok)
                        Write-Host 'Verified normal launch presents four language choices'
                        $step = 1
                        continue
                    }
                    if ($step -eq 0 -or [SetupWindowShape]::ClassName($handle) -ne 'TWizardForm') { continue }
                    if (![SetupWindowShape]::IsRounded($handle)) { continue }
                    $next = Find-ChildByCaption $handle '^Next\s*[\p{P}\p{S}]*$' -Pattern
                    if ($next -eq [IntPtr]::Zero) { continue }
                    if ($step -eq 1) {
                        Write-Host "Observed rounded wizard, next caption [$([SetupWindowShape]::Text($next))]"
                        [SetupWindowShape]::Click($next)
                        $step = 2
                        continue
                    }
                    if ($step -eq 2) {
                        $accept = Find-ChildByCaption $handle 'I accept the agreement'
                        if ($accept -eq [IntPtr]::Zero) { continue }
                        $memo = [SetupWindowShape]::VisibleChildren($handle) |
                            Where-Object { [SetupWindowShape]::ClassName($_) -match $licenseViewerClass } |
                            Select-Object -First 1
                        if (!$memo) { throw 'License page has no visible RichEdit viewer' }
                        $memoLength = [SetupWindowShape]::TextLength($memo)
                        $memoLines = [SetupWindowShape]::LineCount($memo)
                        if (($memoLength -lt $minimumLicenseText -and $memoLines -lt $minimumLicenseLines) -or
                            [SetupWindowShape]::Height($memo) -lt 150 -or ![SetupWindowShape]::CanScrollVertically($memo)) {
                            throw "License viewer does not display a full scrollable document (length=$memoLength, lines=$memoLines)"
                        }
                        if (![SetupWindowShape]::IsWindowEnabled($accept) -or [SetupWindowShape]::IsWindowEnabled($next)) {
                            throw 'License initial acceptance gate is invalid'
                        }
                        [SetupWindowShape]::Click($accept)
                        $step = 3
                        continue
                    }
                    if ($step -eq 3 -and [SetupWindowShape]::IsWindowEnabled($next)) {
                        [SetupWindowShape]::Click($next)
                        $step = 4
                        continue
                    }
                    if ($step -eq 4) {
                        $browse = Find-ChildByCaption $handle '^Browse\s*(?:\.{3}|…)?$' -Pattern
                        if ($browse -ne [IntPtr]::Zero) {
                            Write-Host 'Verified expanded GPL license text, default decline, and acceptance entering the folder page'
                            return
                        }
                    }
                }
            }
            Start-Sleep -Milliseconds 250
        } while ([DateTime]::UtcNow -lt $deadline)
        throw "Could not verify $WindowKind (interactive step $step)"
    }
    catch {
        $process.Refresh()
        if ($process.HasExited) { Write-Host "Probe loader exit code: $($process.ExitCode)" }
        Write-ProbeWindows $testIds
        if (Test-Path -LiteralPath $probeLog) {
            Get-Content -LiteralPath $probeLog -Tail 18 | ForEach-Object { Write-Host "  $_" }
        }
        throw
    }
    finally {
        # Close any disposable probe process that is still running.
        foreach ($testId in @($testIds) | Sort-Object -Descending) {
            Stop-Process -Id $testId -ErrorAction SilentlyContinue
            Wait-Process -Id $testId -Timeout 10 -ErrorAction SilentlyContinue
        }
    }
}

$setup = (Get-Item -LiteralPath $SetupPath).FullName
$bytes = [IO.File]::ReadAllBytes($setup)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
if ([BitConverter]::ToUInt32($bytes, $peOffset) -ne 0x4550 -or [BitConverter]::ToUInt16($bytes, $peOffset + 4) -ne 0x8664) {
    throw 'Setup.exe does not have an x64 PE header'
}
# Inno overwrites a fixed-width VERSIONINFO string and leaves its trailing spaces intact.
$setupVersion = (Get-Item -LiteralPath $setup).VersionInfo
$setupCompany = ([string] $setupVersion.CompanyName).TrimEnd([char] ' ')
if ($setupCompany -cne '71') {
    throw "Setup version resource publisher expected [71], found [$setupCompany]; description [$($setupVersion.FileDescription)]"
}

$target = Join-Path $env:RUNNER_TEMP 'tt tool 安裝測試'
$data = Join-Path $env:LOCALAPPDATA 'tt-tool\data'
$programs = [Environment]::GetFolderPath('Programs')
$shortcutPath = Join-Path $programs 'tt tool\tt tool.lnk'
$unmanagedLink = Join-Path $programs 'tt tool.lnk'
$desktopPath = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'tt tool.lnk'
$appLink = Join-Path $target 'tt tool.lnk'
$log = Join-Path $env:RUNNER_TEMP 'tt-tool-install.log'
foreach ($path in @($target, $data, $shortcutPath, $desktopPath, $unmanagedLink)) {
    if (Test-Path -LiteralPath $path) { throw "Test requires a fresh installer environment: $path" }
}
$flags = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/LOG="' + $log + '"'))
$flags += ('/DIR="' + $target + '"')
$setupProbeFailure = $null
try {
    Test-RoundedWindow $setup @('/NORESTART') 'setup' -ExerciseSetup
}
catch {
    $setupProbeFailure = $_
    Write-Warning "Interactive setup verification failed; continuing other smoke checks: $($_.Exception.Message)"
}
Invoke-Setup $setup ($flags + '/LANG=ko')
$uninstallRegistry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{74A2509B-977F-47DC-8C34-409B3CB77523}_is1'
if ((Get-ItemPropertyValue -LiteralPath $uninstallRegistry -Name Publisher) -ne '71') {
    throw 'Installed-app publisher is not 71'
}
if (!(Test-Path -LiteralPath $shortcutPath -PathType Leaf) -or
    !(Test-Path -LiteralPath $appLink -PathType Leaf) -or (Test-Path -LiteralPath $desktopPath)) {
    throw 'Default install must add Start Menu and in-folder shortcuts only'
}
$pythonw = Join-Path $target 'runtime\pythonw.exe'
$launcher = Join-Path $target 'app\tt_tool_launcher.py'
if (!(Test-Path -LiteralPath (Join-Path $target 'tt-tool.ico'))) { throw 'Installed icon missing' }

$installedPython = Join-Path $target 'runtime\python.exe'
& $installedPython -I -B $launcher --check
if ($LASTEXITCODE -ne 0) { throw 'Installed Qt smoke check failed' }
$uninstaller = Join-Path $target 'unins000.exe'
$checkUninstaller = @'
import sys
from pathlib import Path
expected = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(expected.parent / "app"))
from fisher.maintenance import uninstall_program
actual = uninstall_program(expected.parent)
if actual is None or not actual.samefile(expected):
    raise SystemExit("Registry lookup did not resolve the installed tt tool uninstaller")
'@
& $installedPython -I -B -c $checkUninstaller $uninstaller
if ($LASTEXITCODE -ne 0) { throw 'Installed app could not resolve its registered uninstaller' }
Test-RoundedWindow $uninstaller @('/SILENT', '/NORESTART', '/TTTOOLPROMPT') 'uninstall confirmation'

function Test-ShortcutLaunch([string] $LinkPath, [string] $ExpectedTitle) {
    # ShellExecute follows the real Windows shortcut, including its Unicode path.
    # The legacy WScript.Shell automation accessor can mangle non-ASCII paths.
    $link = [System.Diagnostics.ProcessStartInfo]::new($LinkPath)
    $link.UseShellExecute = $true
    $started = [System.Diagnostics.Process]::Start($link)
    $app = $null
    try {
        $until = [DateTime]::UtcNow.AddSeconds(20)
        do {
            $app = Get-Process -Name pythonw -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -ieq $pythonw } | Select-Object -First 1
            if ($app -and $app.MainWindowTitle -eq $ExpectedTitle) { break }
            Start-Sleep -Milliseconds 250
        } while ([DateTime]::UtcNow -lt $until)
        if (!$app -or $app.MainWindowTitle -ne $ExpectedTitle) {
            throw "Shortcut did not open the installed executable with title [$ExpectedTitle]"
        }
        $null = $app.CloseMainWindow()
        if (!$app.WaitForExit(5000)) { throw 'tt tool did not exit after closing its window' }
        # Get-Process can wait on a discovered process without retaining its exit code.
        if ($started -and $started.Id -eq $app.Id -and $started.ExitCode -ne 0) {
            throw "tt tool exited with $($started.ExitCode)"
        }
        if (Test-Path -LiteralPath (Join-Path $data 'startup-error.log')) {
            throw 'tt tool recorded a launcher error'
        }
    }
    finally {
        if ($app -and !$app.HasExited) { $app.Kill(); $app.WaitForExit() }
    }
}

$pref = Join-Path $data 'tt_tool_ui.json'
if ((Get-Content -LiteralPath $pref -Raw | ConvertFrom-Json).language -ne 'ko') { throw 'Initial setup language was not saved' }
Test-ShortcutLaunch $shortcutPath 'tt tool · 모바일 활동 도우미'
& (Join-Path $PSScriptRoot 'smoke-updater.ps1') -SetupPath $setup -InstallPath $target -ExpectedTitle 'tt tool · 모바일 활동 도우미'
'{"language":"ja"}' | Set-Content -LiteralPath $pref -Encoding utf8NoBOM
'Unmanaged Start Menu entry' | Set-Content -LiteralPath $unmanagedLink -Encoding utf8NoBOM
Invoke-Setup $setup ($flags + '/LANG=zh_TW' + '/TASKS=startmenu,desktop')
if (!(Test-Path -LiteralPath $desktopPath -PathType Leaf)) { throw 'Selected desktop shortcut missing' }
if ((Get-Content -LiteralPath $pref -Raw | ConvertFrom-Json).language -ne 'ja') { throw 'Upgrade changed settings' }
Test-ShortcutLaunch $desktopPath 'tt tool · モバイル活動アシスタント'

$otherTarget = Join-Path $env:RUNNER_TEMP 'tt tool invalid upgrade path'
$movedFlags = $flags[0..($flags.Count - 2)] + ('/DIR="' + $otherTarget + '"')
Invoke-Setup $setup ($movedFlags + '/LANG=en') 7
if (Test-Path -LiteralPath (Join-Path $otherTarget 'app\tt_tool_launcher.py')) {
    throw 'Upgrade installed into a different folder'
}

Invoke-Setup $setup ($flags + '/LANG=en' + '/MERGETASKS=!startmenu,!desktop')
if ((Test-Path -LiteralPath $shortcutPath) -or (Test-Path -LiteralPath $desktopPath)) {
    throw 'Upgrade with both shortcuts cleared did not remove the managed shortcuts'
}
if ((Get-Content -LiteralPath $unmanagedLink -Raw).Trim() -ne 'Unmanaged Start Menu entry') {
    throw 'Upgrade removed or modified an unmanaged Start Menu entry'
}
Test-ShortcutLaunch $appLink 'tt tool · モバイル活動アシスタント'
Test-RoundedWindow $uninstaller @('/SILENT', '/NORESTART', '/TTTOOLCOMPLETE') 'uninstall completion' -ExerciseRemoval
foreach ($path in @($shortcutPath, $desktopPath, $appLink, $launcher)) {
    if (Test-Path -LiteralPath $path) { throw "Uninstall left an installed file or shortcut: $path" }
}
if ((Get-Content -LiteralPath $unmanagedLink -Raw).Trim() -ne 'Unmanaged Start Menu entry') {
    throw 'Uninstall removed or modified an unmanaged Start Menu entry'
}
if ((Get-Content -LiteralPath $pref -Raw | ConvertFrom-Json).language -ne 'ja') { throw 'Uninstall removed settings' }
$dataRootSibling = Join-Path (Split-Path -Parent $data) 'outside-data.txt'
'Unrelated file' | Set-Content -LiteralPath $dataRootSibling -Encoding utf8NoBOM
$diagnostics = New-Item -ItemType Directory -Path (Join-Path $data 'logs')
Set-Content -LiteralPath (Join-Path $diagnostics.FullName 'sample.log') -Value 'Test diagnostics'
Invoke-Setup $setup ($flags + '/LANG=en' + '/MERGETASKS=!startmenu,!desktop')
Invoke-Setup $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TTTOOLCLEARDATA')
if (Test-Path -LiteralPath $data) { throw 'Opt-in uninstall did not remove app data' }
if ((Get-Content -LiteralPath $dataRootSibling -Raw).Trim() -ne 'Unrelated file') {
    throw 'Opt-in uninstall changed a file outside app data'
}
Write-Output 'Verified x64 setup, shortcut choices and launches, upgrade location, uninstall, settings preservation and explicit app data removal'
if ($setupProbeFailure) { throw "Interactive setup verification failed: $($setupProbeFailure.Exception.Message)" }
