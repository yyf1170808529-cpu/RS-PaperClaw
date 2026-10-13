@echo off
setlocal
cd /d "%~dp0"
echo Installing optional offline English-to-Chinese translation.
echo This downloads dependencies and a translation model. Keep this window open.
if exist ".venv-maritime\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto defaultpython
py -3.11 -c "import sys" >nul 2>nul
if errorlevel 1 goto defaultpython
py -3.11 -m venv .venv-maritime
if errorlevel 1 goto failed
goto install
:defaultpython
python -m venv .venv-maritime
if errorlevel 1 goto failed
:install
".venv-maritime\Scripts\python.exe" -m pip install -r skills/rs-paper-pipeline/requirements-translation.txt
if errorlevel 1 goto failed
".venv-maritime\Scripts\python.exe" skills/rs-paper-pipeline/scripts/cli.py maritime --action install-model
if errorlevel 1 goto failed
echo Installation complete. Run translate-maritime.cmd to translate abstracts.
pause
exit /b 0
:failed
echo Installation failed. Copy the error above for troubleshooting.
pause
exit /b 1
