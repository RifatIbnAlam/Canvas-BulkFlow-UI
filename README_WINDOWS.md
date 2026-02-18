# Windows Build + Run

## Build the EXE (one-time on a Windows 11 machine)

1. Install Python 3.11+ for Windows (from python.org).  
   During install, check **"Add Python to PATH"**.
2. Copy this folder to Windows (e.g. `C:\Canvas-BulkFlow\`).
3. Double‑click `build_windows.bat`.

After it finishes, the EXE will be at:

`dist\CanvasBulkFlow.exe`

## Run

Just double‑click `dist\CanvasBulkFlow.exe`.  
It will open your browser automatically at `http://127.0.0.1:5000`.

No Python or dependencies are required on staff machines once you have the EXE.

## Keep API token local (recommended)

1. Copy `canvas_bulkflow.env.example` to `canvas_bulkflow.env`.
2. Edit `canvas_bulkflow.env` and set:
   `CANVAS_API_TOKEN=...`
3. Rebuild the EXE if needed.

The app pre-fills the token from `canvas_bulkflow.env`, and `.gitignore` excludes this file so it is not pushed to GitHub.
