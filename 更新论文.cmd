@echo off
chcp 65001 >nul
set PYTHONUTF8=1
setlocal
cd /d "%~dp0"
set "maritime_python=python"
if exist ".venv-maritime\Scripts\python.exe" set "maritime_python=%~dp0.venv-maritime\Scripts\python.exe"
"%maritime_python%" skills/rs-paper-pipeline/scripts/update_maritime.py %*
set "maritime_exit=%errorlevel%"
pause
exit /b %maritime_exit%
