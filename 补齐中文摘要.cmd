@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv-maritime\Scripts\python.exe" (
  echo Translation environment is missing. Run install-translation.cmd first.
  pause
  exit /b 1
)
"%~dp0.venv-maritime\Scripts\python.exe" -u skills/rs-paper-pipeline/scripts/cli.py maritime --action translate-history %*
set "maritime_exit=%errorlevel%"
echo Finished. Exit code: %maritime_exit%
pause
exit /b %maritime_exit%
