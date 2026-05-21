@echo off
REM shortvideo-skill Windows インストーラ (cmd ラッパー)
REM 内部で PowerShell を呼び出して install.ps1 を実行する
powershell.exe -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
