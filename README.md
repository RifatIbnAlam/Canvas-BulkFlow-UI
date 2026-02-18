# Canvas-BulkFlow-UI

Bulk download scanned PDFs from Canvas, OCR them via Abbyy FineReader Hot Folder, and upload back to Canvas with a simple UI.

## Features
- Friendly local web UI (no terminal needed for staff)
- One-click Download and Upload
- Live progress and logs
- Windows `.exe` build support

## Quickstart (Mac)
1. Install Python 3.11+.
2. Install dependencies:
   ```bash
   python3 -m pip install --user -r requirements.txt
   ```
3. Set your API token:
   ```bash
   cp canvas_bulkflow.env.example canvas_bulkflow.env
   ```
   Edit `canvas_bulkflow.env` and set `CANVAS_API_TOKEN`.
4. Run the UI:
   ```bash
   python3 canvas_bulkflow_web.py
   ```
5. Open `http://127.0.0.1:5000` (auto-opens on most systems).

## Quickstart (Windows)
1. Install Python 3.11+ (from [python.org](https://www.python.org/downloads/)). Check **Add Python to PATH**.
2. Copy the folder to `C:\Canvas-BulkFlow\`.
3. Create `C:\Canvas-BulkFlow\canvas_bulkflow.env` with:
   ```
   CANVAS_API_TOKEN=YOUR_CANVAS_API_TOKEN_HERE
   CANVAS_BASE_URL=https://usu.instructure.com
   ```
4. Build the EXE:
   ```
   C:\Canvas-BulkFlow\build_windows.bat
   ```
5. Run:
   ```
   C:\Canvas-BulkFlow\dist\CanvasBulkFlow.exe
   ```

## Workflow
1. Export Ally Institution Report CSV from Canvas.
2. Use the UI to download scanned PDFs into `Downloads`.
3. Abbyy FineReader Hot Folder OCRs into `Downloads\OCRed`.
4. Use the UI to upload OCRed PDFs back to Canvas.

## Configuration
Set environment variables in `canvas_bulkflow.env` (not committed):
- `CANVAS_API_TOKEN` (required)
- `CANVAS_BASE_URL` (optional, defaults to `https://usu.instructure.com`)

## Project Layout
- `canvas_bulkflow_web.py` - web UI
- `canvas_bulk_download.py` - download script
- `canvas_bulk_upload.py` - upload script
- `build_windows.bat` - Windows build script
- `canvas_bulkflow.spec` - PyInstaller spec

## Security
Never commit your Canvas API token. Use `canvas_bulkflow.env` locally.
