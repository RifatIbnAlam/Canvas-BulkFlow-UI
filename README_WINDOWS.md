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

## API Token (Do Not Commit)

Create `canvas_bulkflow.env` in the same folder as the EXE with:

`CANVAS_API_TOKEN=YOUR_CANVAS_API_TOKEN_HERE`

You can copy `canvas_bulkflow.env.example` and rename it.
