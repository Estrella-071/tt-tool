# SPDX-License-Identifier: GPL-3.0-only
# Intended for a disposable Windows x64 GitHub Actions runner.
param([Parameter(Mandatory)] [string] $SetupPath, [string] $LegacySetupPath)

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
    private struct Point { public int X, Y; }
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
    private static extern bool GetClientRect(IntPtr window, out Rect bounds);
    [DllImport("user32.dll")]
    private static extern bool ClientToScreen(IntPtr window, ref Point position);
    [DllImport("user32.dll")]
    private static extern uint GetDpiForWindow(IntPtr window);
    [DllImport("user32.dll", EntryPoint = "GetWindowLongW")]
    private static extern int GetWindowLong(IntPtr window, int index);
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

    public static bool HasNativeFrame(IntPtr window) {
        const int wsCaption = 0x00c00000;
        if ((GetWindowLong(window, -16) & wsCaption) != wsCaption) return false;
        var region = CreateRectRgn(0, 0, 0, 0);
        try { return GetWindowRgn(window, region) == 0; }
        finally { DeleteObject(region); }
    }

    public static IntPtr[] VisibleWindows(int processId) {
        var windows = new List<IntPtr>();
        EnumWindows((window, unused) => {
            GetWindowThreadProcessId(window, out int owner);
            if ((processId == 0 || owner == processId) && IsWindowVisible(window)) windows.Add(window);
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }

    public static int OwnerProcessId(IntPtr window) {
        GetWindowThreadProcessId(window, out int owner);
        return owner;
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

    private static bool FitsInside(IntPtr window, Rect bounds, IntPtr topLevel) {
        for (IntPtr parent = GetParent(window); parent != IntPtr.Zero; parent = GetParent(parent)) {
            var origin = new Point();
            if (!GetClientRect(parent, out Rect client) || !ClientToScreen(parent, ref origin)
                || bounds.Left < origin.X || bounds.Top < origin.Y
                || bounds.Right > origin.X + client.Right || bounds.Bottom > origin.Y + client.Bottom)
                return false;
            if (parent == topLevel) return true;
        }
        return false;
    }

    public static bool FolderControlsFit(IntPtr wizard, IntPtr edit, IntPtr button) {
        if (GetParent(edit) != GetParent(button)
            || !GetWindowRect(edit, out Rect path) || !GetWindowRect(button, out Rect browse))
            return false;
        uint dpi = GetDpiForWindow(wizard);
        int gap = browse.Left - path.Right;
        return dpi > 0 && browse.Right - browse.Left >= 110 * dpi / 96
            && browse.Bottom - browse.Top >= 32 * dpi / 96
            && gap >= 8 * dpi / 96 && Math.Abs(path.Top + path.Bottom - browse.Top - browse.Bottom) <= 4
            && FitsInside(edit, path, wizard) && FitsInside(button, browse, wizard);
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

$licensePath = Join-Path (Split-Path -Parent $PSScriptRoot) 'LICENSE'
$sourceLicense = Get-Content -Raw -LiteralPath $licensePath
if ($sourceLicense -notmatch 'GNU GENERAL PUBLIC LICENSE\s+Version 3' -or $sourceLicense.Length -lt 30000) {
    throw 'The packaged source license must be the complete GNU GPL version 3'
}

function Find-ChildByCaption([IntPtr] $Window, [string] $Caption, [switch] $Pattern, [switch] $Button) {
    foreach ($child in [SetupWindowShape]::VisibleChildren($Window)) {
        if ($Button -and [SetupWindowShape]::ClassName($child) -notlike '*Button') { continue }
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
            $nativeFrame = [SetupWindowShape]::HasNativeFrame($handle)
            Write-Host "  $windowClass caption=[$caption] nativeFrame=$nativeFrame height=$([SetupWindowShape]::Height($handle))"
            foreach ($child in [SetupWindowShape]::VisibleChildren($handle)) {
                $childClass = [SetupWindowShape]::ClassName($child)
                if ($childClass -notmatch 'Button|Radio|Static|Label|Edit') { continue }
                $childText = [SetupWindowShape]::Text($child) -replace '\s+', ' '
                if ($childText.Length -gt 240) { $childText = $childText.Substring(0, 240) }
                Write-Host "    $childClass [$childText] enabled=$([SetupWindowShape]::IsWindowEnabled($child))"
            }
        }
    }
}

function Test-InstallerWindow([string] $Application, [string[]] $Flags, [string] $WindowKind,
    [switch] $ExerciseSetup, [switch] $ExerciseRemoval, [string] $ConfirmInstallPath,
    [Diagnostics.Process] $RunningApp, [switch] $DeclineClose, [string] $SetupLanguage = "en") {
    $probeLog = Join-Path $env:RUNNER_TEMP "tt-tool-interactive-$($WindowKind -replace ' ', '-').log"
    $Flags += ('/LOG="' + $probeLog + '"')
    if ($ExerciseSetup -and $SetupLanguage -ne 'en') { $Flags += "/LANG=$SetupLanguage" }
    $process = Start-Process -FilePath $Application -ArgumentList $Flags -WindowStyle Normal -PassThru
    $testIds = [Collections.Generic.HashSet[int]]::new()
    $null = $testIds.Add($process.Id)
    $step = if ($ExerciseSetup -and $SetupLanguage -ne 'en') { 1 } else { 0 }
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
                        if ($ConfirmInstallPath -and $step -eq 0) {
                            $remove = Find-ChildByCaption $handle 'Uninstall' -Button
                            if ($remove -eq [IntPtr]::Zero) { continue }
                            $pathField = Find-ChildByCaption $handle $ConfirmInstallPath
                            $dataToggle = Find-ChildByCaption $handle 'Also clear settings, calibration, and diagnostic logs'
                            if (![SetupWindowShape]::HasNativeFrame($handle) -or
                                $pathField -eq [IntPtr]::Zero -or $dataToggle -eq [IntPtr]::Zero) {
                                throw 'The removal confirmation lacks its installed path or data option'
                            }
                            [SetupWindowShape]::Click($remove)
                            $step = 1
                            continue
                        }
                        if ($RunningApp -and $step -eq 1) {
                            $question = Find-ChildByCaption $handle 'tt tool is still running. Close it and continue uninstalling?'
                            if ($question -eq [IntPtr]::Zero) { continue }
                            $choice = if ($DeclineClose) { 'No' } else { 'Yes' }
                            $button = Find-ChildByCaption $handle $choice -Button
                            if ($button -eq [IntPtr]::Zero) { throw "The running-app prompt lacks $choice" }
                            [SetupWindowShape]::Click($button)
                            if ($DeclineClose) {
                                if (!$process.WaitForExit(10000) -or $RunningApp.HasExited -or
                                    !(Test-Path -LiteralPath $Application -PathType Leaf)) {
                                    throw 'Declining to close the app did not cancel the removal safely'
                                }
                                Write-Host 'Verified declining the running-app prompt preserves the app and installation'
                                return
                            }
                            if (!$RunningApp.WaitForExit(10000)) {
                                throw 'The app did not close after the uninstall confirmation'
                            }
                            Write-Host 'Verified the Installed Apps confirmation shows the folder and closes tt tool'
                            $step = 2
                            continue
                        }
                        $releases = Find-ChildByCaption $handle 'Open the latest stable release'
                        $close = Find-ChildByCaption $handle 'Close'
                        if ($releases -ne [IntPtr]::Zero -and $close -ne [IntPtr]::Zero) {
                            if (![SetupWindowShape]::HasNativeFrame($handle)) {
                                throw 'Uninstall completion is missing its native caption and frame'
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
                        if ([SetupWindowShape]::HasNativeFrame($handle)) {
                            Write-Host "Observed native $WindowKind window ($([SetupWindowShape]::Text($handle)))."
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
                    if (![SetupWindowShape]::HasNativeFrame($handle)) { continue }
                    if ($step -eq 1) {
                        $next = Find-ChildByCaption $handle '^(?:Next|下一步|次へ|다음)\s*(?:\(N\))?\s*>?$' -Pattern -Button
                        if ($next -eq [IntPtr]::Zero) { continue }
                        [SetupWindowShape]::Click($next)
                        $step = 2
                        continue
                    }
                    if ($step -eq 2) {
                        $browse = Find-ChildByCaption $handle '^(?:Browse|瀏覽|参照|찾아보기)\s*(?:\(R\))?\s*(?:\.{3}|…)?$' -Pattern -Button
                        if ($browse -eq [IntPtr]::Zero) { continue }
                        $path = [SetupWindowShape]::VisibleChildren($handle) |
                            Where-Object { [SetupWindowShape]::ClassName($_) -like '*PathEdit' } |
                            Select-Object -First 1
                        if (!$path -or ![SetupWindowShape]::FolderControlsFit($handle, $path, $browse)) {
                            throw "The $SetupLanguage folder field or Browse button is clipped or misaligned"
                        }
                        Write-Host "Verified $SetupLanguage folder controls fit and are reachable directly from Welcome"
                        return
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
    foreach ($language in @('en', 'zh_TW', 'ja', 'ko')) {
        Test-InstallerWindow $setup @('/NORESTART') "setup-$language" -ExerciseSetup -SetupLanguage $language
    }
}
catch {
    $setupProbeFailure = $_
    Write-Warning "Interactive setup verification failed; continuing other smoke checks: $($_.Exception.Message)"
}
Invoke-Setup $setup ($flags + '/LANG=ko')
$installedLicense = Join-Path $target 'LICENSE'
if (!(Test-Path -LiteralPath $installedLicense -PathType Leaf) -or
        (Get-FileHash -LiteralPath $installedLicense).Hash -cne (Get-FileHash -LiteralPath $licensePath).Hash) {
    throw 'Setup did not ship the complete and unmodified GNU GPL license'
}
Write-Host 'Verified the installed GNU GPL license matches the source'
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
Test-InstallerWindow $uninstaller @('/SILENT', '/NORESTART', '/TTTOOLPROMPT') 'uninstall confirmation'

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
# The locally built setup in the upgrade fixture has no external origin. Exercise
# the installed downloader's Internet-zone marker separately on real NTFS.
$checkDownloadMarker = @"
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "app"))
from fisher.updater import InstallerFile, UpdateAsset

payload = b"tt tool Windows update smoke data"
asset = UpdateAsset(
    "tt-tool-9.0.0-windows-x64-setup.exe", "", len(payload),
    hashlib.sha256(payload).hexdigest(),
)
download = InstallerFile(asset)
try:
    download.write(payload)
    download.verify()
    assert download.installer.read_bytes() == payload
    with open(str(download.installer) + ":Zone.Identifier", "rb") as marker:
        assert marker.read().splitlines() == [b"[ZoneTransfer]", b"ZoneId=3"]
finally:
    download.cleanup()
assert not download.directory.exists()
print("Verified Windows Internet-zone marking and cleanup of a downloaded update")
"@
& $installedPython -I -B -c $checkDownloadMarker $target
if ($LASTEXITCODE -ne 0) { throw 'Installed updater did not mark and clean its verified download' }
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
$registeredCommand = Get-ItemPropertyValue -LiteralPath $uninstallRegistry -Name UninstallString
if ($registeredCommand -cne ('"' + $uninstaller + '" /SILENT /NORESTART /TTTOOLPROMPT')) {
    throw 'Windows Installed Apps does not open the guided uninstaller'
}
$runningApp = Start-Process -FilePath $pythonw -ArgumentList @('-I', '-B', ('"' + $launcher + '"')) -PassThru
try {
    $ready = [DateTime]::UtcNow.AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 250
        $runningApp.Refresh()
    } until ($runningApp.MainWindowTitle -or $runningApp.HasExited -or [DateTime]::UtcNow -ge $ready)
    if ($runningApp.HasExited -or !$runningApp.MainWindowTitle) {
        throw 'The deployed app could not start before uninstall verification'
    }
    $uninstallFlags = @('/SILENT', '/NORESTART', '/TTTOOLPROMPT')
    Test-InstallerWindow $uninstaller $uninstallFlags 'decline closing running app' `
        -ExerciseRemoval -ConfirmInstallPath $target -RunningApp $runningApp -DeclineClose
    Test-InstallerWindow $uninstaller $uninstallFlags 'uninstall completion' `
        -ExerciseRemoval -ConfirmInstallPath $target -RunningApp $runningApp
}
finally {
    if (!$runningApp.HasExited) { $runningApp.Kill(); $runningApp.WaitForExit() }
}
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

if ($LegacySetupPath) {
    $legacySetup = Get-Item -LiteralPath $LegacySetupPath
    if ($legacySetup.Length -ne 120630602 -or (Get-FileHash -LiteralPath $legacySetup.FullName).Hash -ine
        '78865f5a4e3a26a6abbece1dc5560e2adef964fd76873eea641c8e5415f1651b') {
        throw 'The legacy installer does not match the original v1.3.0 release'
    }
    if ((Test-Path -LiteralPath $uninstallRegistry) -or (Test-Path -LiteralPath $launcher) -or
        (Test-Path -LiteralPath $data)) {
        throw 'The renumbering migration fixture requires an uninstalled app with no data'
    }

    $quiet = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LANG=en', '/MERGETASKS=!startmenu,!desktop')
    Invoke-Setup $legacySetup.FullName ($quiet + ('/DIR="' + $target + '"'))
    $before = Get-ItemProperty -LiteralPath $uninstallRegistry
    if ($before.DisplayVersion -ne '1.3.0' -or $before.'Inno Setup: App Path' -ine $target) {
        throw 'The migration fixture did not install v1.3.0 into the expected folder'
    }

    $savedPreferences = '{"language":"ja","migrationFixture":"keep"}'
    Set-Content -LiteralPath $pref -Value $savedPreferences -Encoding utf8NoBOM -NoNewline
    # Let the new setup find the previous install itself, just as in a manual update.
    Invoke-Setup $setup $quiet
    $after = Get-ItemProperty -LiteralPath $uninstallRegistry
    $expected = @($setupVersion.FileMajorPart, $setupVersion.FileMinorPart, $setupVersion.FileBuildPart) -join '.'
    $checkVersion = 'import sys; sys.path.insert(0, sys.argv[1]); from fisher.project import VERSION; print(VERSION)'
    $actual = & $installedPython -I -B -c $checkVersion (Join-Path $target 'app')
    if ($LASTEXITCODE -ne 0 -or $after.DisplayVersion -ne $expected -or $actual -cne $expected -or
        $after.'Inno Setup: App Path' -ine $target -or (Get-Content -LiteralPath $pref -Raw) -cne $savedPreferences) {
        throw "Migration from v1.3.0 did not preserve the installation and settings or install v$expected"
    }
    Test-ShortcutLaunch $appLink 'tt tool · モバイル活動アシスタント'
    Write-Output "Verified migration from v1.3.0 to v$expected in the existing folder with the saved settings"
}
