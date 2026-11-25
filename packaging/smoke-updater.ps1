# SPDX-License-Identifier: GPL-3.0-only
# Exercise the native handoff on the disposable Windows installer runner.
param(
    [Parameter(Mandatory)] [string] $SetupPath,
    [Parameter(Mandatory)] [string] $InstallPath,
    [Parameter(Mandatory)] [string] $ExpectedTitle
)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'The updater test requires a disposable Windows runner' }

function Get-UpdateWindows([int] $HelperId, [string] $InstallerName) {
    foreach ($handle in ([SetupWindowShape]::VisibleWindows(0) | Select-Object -First 80)) {
        $title = [SetupWindowShape]::Text($handle)
        if (!$title) { continue }
        $ownerId = [SetupWindowShape]::OwnerProcessId($handle)
        $owner = Get-Process -Id $ownerId -ErrorAction SilentlyContinue
        if ($ownerId -eq $HelperId -or $owner.ProcessName -eq $InstallerName -or
                $title -match 'Security Warning|SmartScreen|protected your PC|tt tool|Windows Security|User Account Control') {
            [pscustomobject]@{Owner = $owner.ProcessName; Handle = $handle; Title = $title}
        }
    }
}

function Confirm-FixtureDownload([object[]] $Windows, [string] $Installer, [string] $Hash) {
    if ($env:RUNNER_ENVIRONMENT -ne 'github-hosted') { return $false }
    foreach ($window in $Windows) {
        if ($window.Title -cne 'Open File - Security Warning' -or
                [SetupWindowShape]::ClassName($window.Handle) -cne '#32770') { continue }
        $children = @([SetupWindowShape]::VisibleChildren($window.Handle) | Select-Object -First 24)
        $name = [IO.Path]::GetFileName($Installer)
        $matching = @($children | Where-Object {
            [SetupWindowShape]::Text($_).IndexOf($name, [StringComparison]::OrdinalIgnoreCase) -ge 0
        })
        $run = @($children | Where-Object {
            [SetupWindowShape]::ClassName($_) -ieq 'Button' -and
                ([SetupWindowShape]::Text($_) -replace '&', '') -ceq 'Run'
        })
        if (!$matching.Count -or $run.Count -ne 1) { continue }
        if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash -ine $Hash) {
            throw 'Windows security warning does not refer to the verified installer bytes'
        }
        [SetupWindowShape]::Click($run[0])
        Write-Host 'Accepted the normal Windows Run confirmation for the checksum-verified CI fixture'
        return $true
    }
    return $false
}

function Wait-UpdateHandoff([Diagnostics.Process] $Process, [string] $Installer, [string] $Hash, [string] $Trace) {
    $ready = [DateTime]::UtcNow.AddSeconds(120)
    $accepted = $false
    $windows = @()
    do {
        if ($Process.WaitForExit(400)) { break }
        $phases = Get-Content -LiteralPath $Trace -Tail 20 -ErrorAction SilentlyContinue
        if ($phases -match 'showing update failure dialog') { break }
        $windows = @(Get-UpdateWindows $Process.Id ([IO.Path]::GetFileNameWithoutExtension($Installer)))
        if (!$accepted -and $windows.Count -and $phases -match 'opening marked installer') {
            $accepted = Confirm-FixtureDownload $windows $Installer $Hash
        }
    } while ([DateTime]::UtcNow -lt $ready)

    Get-Content -LiteralPath $Trace -Tail 20 -ErrorAction SilentlyContinue | Write-Host
    if (!$Process.HasExited) {
        $windows = @(Get-UpdateWindows $Process.Id ([IO.Path]::GetFileNameWithoutExtension($Installer)))
        $windows | Select-Object -First 12 | ForEach-Object { Write-Host "Update window: $($_.Owner) / $($_.Title)" }
        if ($phases -match 'showing update failure dialog') { throw 'The update helper showed its failure dialog' }
        throw 'Update handoff did not finish'
    }
    if ($Process.ExitCode -ne 0) { throw "Update handoff failed ($($Process.ExitCode))" }
}

$runtime = Join-Path $InstallPath 'runtime\pythonw.exe'
$launcher = Join-Path $InstallPath 'app\tt_tool_launcher.py'
$helper = @(Get-ChildItem -LiteralPath (Join-Path $InstallPath 'app') -Filter 'tt-tool-update-*.exe')
if ($helper.Count -ne 1) { throw 'The installed update helper is missing or ambiguous' }

# Each published version has its own helper filename. Use a disposable name so
# this same-version fixture has the same file-lock behavior as a real upgrade.
$testHelper = Join-Path $InstallPath 'app\update-smoke-handoff.exe'
$download = Join-Path ([IO.Path]::GetTempPath()) ('tt-tool-update-' + [Guid]::NewGuid().ToString('N'))
$installer = Join-Path $download (Split-Path -Leaf $SetupPath)
$trace = "$download.handoff.log"
$preferences = Join-Path $env:LOCALAPPDATA 'tt-tool\data\tt_tool_ui.json'
$savedPreferences = Get-Content -LiteralPath $preferences -Raw
$original = $null
$handoff = $null
$reopened = $null

try {
    Copy-Item -LiteralPath $helper[0].FullName -Destination $testHelper
    New-Item -Path $download -ItemType Directory | Out-Null
    Copy-Item -LiteralPath $SetupPath -Destination $installer
    $hash = (Get-FileHash -LiteralPath $SetupPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ine $hash) {
        throw 'Copied update fixture does not match the built installer'
    }
    $original = Start-Process -FilePath $runtime -ArgumentList @('-I', '-B', ('"' + $launcher + '"')) -PassThru
    $ready = [DateTime]::UtcNow.AddSeconds(20)
    do {
        Start-Sleep -Milliseconds 250
        $original.Refresh()
        if ($original.HasExited) { throw 'The app exited before updater verification' }
    } while ($original.MainWindowTitle -ne $ExpectedTitle -and [DateTime]::UtcNow -lt $ready)
    if ($original.MainWindowTitle -ne $ExpectedTitle) { throw 'The installed app did not open' }

    $arguments = @($original.Id.ToString(), $original.StartTime.ToFileTimeUtc().ToString(),
        ('"' + $installer + '"'), $hash, '"tt tool update test"', '"The update did not finish."')
    $handoff = Start-Process -FilePath $testHelper -ArgumentList $arguments -WindowStyle Hidden `
        -RedirectStandardOutput $trace -PassThru
    Start-Sleep -Milliseconds 400
    if ($handoff.HasExited -or !(Test-Path -LiteralPath $installer -PathType Leaf)) {
        throw 'Handoff did not wait for the running app'
    }
    if (!$original.CloseMainWindow() -or !$original.WaitForExit(12000)) {
        throw 'The installed app could not close before the update'
    }
    Wait-UpdateHandoff $handoff $installer $hash $trace
    if ((Test-Path -LiteralPath $download) -or
        (Get-Content -LiteralPath $preferences -Raw) -cne $savedPreferences) {
        throw 'The update left its download behind or modified preferences'
    }
    $ready = [DateTime]::UtcNow.AddSeconds(20)
    do {
        $reopened = Get-Process -Name pythonw -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -ieq $runtime -and $_.MainWindowTitle -eq $ExpectedTitle } |
            Select-Object -First 1
        if ($reopened) { break }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $ready)
    if (!$reopened) { throw 'The updater did not reopen the installed app' }
    $closeEvent = [Threading.EventWaitHandle]::OpenExisting('Estrella071.tt-tool.Close')
    try {
        if (!$closeEvent.Set() -or !$reopened.WaitForExit(12000)) {
            throw 'The updated app did not exit on the installer close request'
        }
    }
    finally {
        $closeEvent.Dispose()
    }
    Write-Output 'Verified update waits for app exit, installs in place, removes its download and reopens with saved preferences'
}
finally {
    foreach ($process in @($original, $handoff, $reopened)) {
        if ($process -and !$process.HasExited) { $process.Kill(); $process.WaitForExit() }
    }
    Remove-Item -LiteralPath $testHelper -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $installer -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $download -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $trace -ErrorAction SilentlyContinue
}
