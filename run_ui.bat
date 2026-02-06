@echo off
setlocal
cd /d %~dp0

py -3 canvas_bulkflow_ui.py
if errorlevel 1 python canvas_bulkflow_ui.py

pause
