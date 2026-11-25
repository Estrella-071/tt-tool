# Windows 單檔建置；需要 Python、PyInstaller、PySide6 與 requirements.txt。
param([Parameter(Mandatory=$true)][string]$PlatformTools, [Parameter(Mandatory=$true)][string]$FFmpeg)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$adb = Join-Path $PlatformTools 'adb.exe'
$adbApi = Join-Path $PlatformTools 'AdbWinApi.dll'
$adbUsb = Join-Path $PlatformTools 'AdbWinUsbApi.dll'
foreach ($item in @($adb,$adbApi,$adbUsb,$FFmpeg)) { if (!(Test-Path -LiteralPath $item -PathType Leaf)) { throw "找不到檔案：$item" } }
$taskPython = (Get-Command python).Source
$env:PATH = (Join-Path $env:WINDIR 'System32') + ';' + $env:WINDIR
& $taskPython -m PyInstaller --noconfirm --onefile --windowed --collect-all dxcam --name SweepAssistant --add-binary "$adb;tools" --add-binary "$adbApi;tools" --add-binary "$adbUsb;tools" --add-binary "$FFmpeg;tools" sweep_desktop.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 建置失敗' }
