@echo off
setlocal enabledelayedexpansion

cd /d %~dp0

echo [1/4] Creating virtual environment...
py -3 -m venv .venv
if errorlevel 1 (
  echo Failed to create venv. Ensure Python 3 is installed.
  exit /b 1
)

echo [2/4] Installing dependencies...
call .venv\Scripts\pip.exe install --upgrade pip
call .venv\Scripts\pip.exe install -r requirements.txt
call .venv\Scripts\pip.exe install pyinstaller

echo [3/4] Building EXE...
call .venv\Scripts\pyinstaller.exe --clean --noconfirm canvas_bulkflow.spec
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [4/4] Done.
echo EXE is at: %cd%\dist\CanvasBulkFlow.exe
pause
