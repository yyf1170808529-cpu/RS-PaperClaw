@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-maritime\Scripts\python.exe" (
  echo Run install-translation.cmd first.
  pause
  exit /b 1
)
set "maritime_count=5"
set /p "maritime_count=Number of top-ranked abstracts to translate [5]: "
".venv-maritime\Scripts\python.exe" skills/rs-paper-pipeline/scripts/cli.py maritime --action translate --limit "%maritime_count%"
if errorlevel 1 (
  echo Some translations failed. Copy the error above for troubleshooting.
  pause
  exit /b 1
)
echo Translation complete. Refresh the reading page.
pause
