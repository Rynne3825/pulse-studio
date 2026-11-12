@echo off
title The Pulse Studio
cd /d "%~dp0"
echo Dang khoi chay The Pulse Studio...
".venv\Scripts\streamlit.exe" run app\app.py
pause
