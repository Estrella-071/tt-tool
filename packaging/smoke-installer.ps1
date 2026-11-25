# SPDX-License-Identifier: GPL-3.0-only
# Intended for a disposable Windows x64 GitHub Actions runner.
param([Parameter(Mandatory)] [string] $SetupPath)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run this install/uninstall test on the disposable Windows runner' }

function Invoke-Setup([string] $Application, [string[]] $Flags) {
    $process = Start-Process -FilePath $Application -ArgumentList $Flags -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "$Application exited with $($process.ExitCode)" }
}

$setup = (Get-Item -LiteralPath $SetupPath).FullName
$bytes = [IO.File]::ReadAllBytes($setup)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
if ([BitConverter]::ToUInt32($bytes, $peOffset) -ne 0x4550 -or [BitConverter]::ToUInt16($bytes, $peOffset + 4) -ne 0x8664) {
    throw 'Setup.exe does not have an x64 PE header'
}

$target = Join-Path $env:RUNNER_TEMP 'tt tool 安裝測試'
$data = Join-Path $env:LOCALAPPDATA 'tt-tool\data'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Programs')) 'tt tool\tt tool.lnk'
$log = Join-Path $env:RUNNER_TEMP 'tt-tool-install.log'
if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $shortcutPath) -or (Test-Path -LiteralPath $data)) {
    throw 'Test requires a fresh installer environment'
}
$flags = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/DIR="' + $target + '"'), ('/LOG="' + $log + '"'))
Invoke-Setup $setup ($flags + '/LANG=ko')
if (!(Test-Path -LiteralPath $shortcutPath -PathType Leaf)) { throw 'Start Menu shortcut missing' }
$pythonw = Join-Path $target 'runtime\pythonw.exe'
$launcher = Join-Path $target 'app\tt_tool_launcher.py'
if (!(Test-Path -LiteralPath (Join-Path $target 'tt-tool.ico'))) { throw 'Installed icon missing' }

$installedPython = Join-Path $target 'runtime\python.exe'
& $installedPython -I -B $launcher --check
if ($LASTEXITCODE -ne 0) { throw 'Installed Qt smoke check failed' }

function Test-ShortcutLaunch([string] $ExpectedTitle) {
    # ShellExecute follows the real Windows shortcut, including its Unicode path.
    # The legacy WScript.Shell automation accessor can mangle non-ASCII paths.
    $link = [System.Diagnostics.ProcessStartInfo]::new($shortcutPath)
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
Test-ShortcutLaunch 'tt tool · 모바일 활동 도우미'
'{"language":"ja"}' | Set-Content -LiteralPath $pref -Encoding utf8NoBOM
Invoke-Setup $setup ($flags + '/LANG=zh_TW')
if ((Get-Content -LiteralPath $pref -Raw | ConvertFrom-Json).language -ne 'ja') { throw 'Upgrade changed settings' }
Test-ShortcutLaunch 'tt tool · モバイル活動アシスタント'
Invoke-Setup (Join-Path $target 'unins000.exe') @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
if ((Test-Path -LiteralPath $shortcutPath) -or (Test-Path -LiteralPath $launcher)) { throw 'Uninstall left the shortcut or app' }
if ((Get-Content -LiteralPath $pref -Raw | ConvertFrom-Json).language -ne 'ja') { throw 'Uninstall removed settings' }
Write-Output 'Verified x64 setup, Start Menu launch, upgrade, uninstall and settings preservation'
