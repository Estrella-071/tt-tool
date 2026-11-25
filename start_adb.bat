@echo off
cd /d "%~dp0"
python qt_fishing.py
if errorlevel 1 pause
