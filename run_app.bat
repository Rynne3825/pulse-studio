@echo off
title He Thong Toi Uu Bai Dang Mang Xa Hoi
cd /d "%~dp0"
set PYTHONPYCACHEPREFIX=%~dp0.cache\pycache
echo Dang khoi chay Streamlit Dashboard...
".venv\Scripts\streamlit.exe" run app\app.py
pause
