@echo off
title The Pulse Editorial Studio
cd /d "%~dp0"
echo Dang khoi chay The Pulse Editorial Studio...
".venv\Scripts\streamlit.exe" run app\app.py
pause
