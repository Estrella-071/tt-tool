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

$setup = (Get-Item -LiteralPath $SetupPath).FullName
$bytes = [IO.File]::ReadAllBytes($setup)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
if ([BitConverter]::ToUInt32($bytes, $peOffset) -ne 0x4550 -or [BitConverter]::ToUInt16($bytes, $peOffset + 4) -ne 0x8664) {
    throw 'Setup.exe does not have an x64 PE header'
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
Invoke-Setup $setup ($flags + '/LANG=ko')
if (!(Test-Path -LiteralPath $shortcutPath -PathType Leaf) -or
    !(Test-Path -LiteralPath $appLink -PathType Leaf) -or (Test-Path -LiteralPath $desktopPath)) {
    throw 'Default install must add Start Menu and in-folder shortcuts only'
}
$pythonw = Join-Path $target 'runtime\pythonw.exe'
$launcher = Join-Path $target 'app\tt_tool_launcher.py'
foreach ($file in @('tt-tool.ico', 'uninstall-mark.png')) {
    if (!(Test-Path -LiteralPath (Join-Path $target $file))) { throw "Installed image missing: $file" }
}

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
Invoke-Setup $uninstaller @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
foreach ($path in @($shortcutPath, $desktopPath, $appLink, $launcher, (Join-Path $target 'uninstall-mark.png'))) {
    if (Test-Path -LiteralPath $path) { throw "Uninstall left an installed file or shortcut: $path" }
}
if ((Get-Content -LiteralPath $unmanagedLink -Raw).Trim() -ne 'Unmanaged Start Menu entry') {
    throw 'Uninstall removed or modified an unmanaged Start Menu entry'
}
if ((Get-Content -LiteralPath $pref -Raw | ConvertFrom-Json).language -ne 'ja') { throw 'Uninstall removed settings' }
Write-Output 'Verified x64 setup, shortcut choices and launches, upgrade location, uninstall, and settings preservation'
