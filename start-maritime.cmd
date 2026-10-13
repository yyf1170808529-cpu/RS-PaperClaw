@echo off
python "%~dp0skills\rs-paper-pipeline\scripts\preview_maritime.py" %*
if errorlevel 1 pause
