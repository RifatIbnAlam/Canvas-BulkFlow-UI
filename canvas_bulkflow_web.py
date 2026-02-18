import io
import os
import tempfile
import threading
import traceback
import uuid
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from flask import Flask, jsonify, render_template_string, request
from canvas_bulkflow_config import load_env_file

from canvas_bulk_download import (
    run_download,
    DEFAULT_BASE_URL as DOWNLOAD_BASE_URL,
    DEFAULT_OUTPUT_FOLDER,
)
from canvas_bulk_upload import (
    bulk_replace_ocr_files,
    DEFAULT_OCR_FOLDER,
)


app = Flask(__name__)
load_env_file()

JOBS = {}
JOBS_LOCK = threading.Lock()


class JobLogWriter:
    def __init__(self, job_id):
        self.job_id = job_id

    def write(self, msg):
        if not msg:
            return
        with JOBS_LOCK:
            job = JOBS.get(self.job_id)
            if job:
                job["log"] += msg

    def flush(self):
        pass


def update_progress(job_id, current, total, message):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job:
            job["current"] = current
            job["total"] = total
            job["message"] = message


def run_job(job_id, action, csv_path, params):
    writer = JobLogWriter(job_id)
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job:
            job["status"] = "running"
            job["message"] = "Starting..."

    try:
        with redirect_stdout(writer), redirect_stderr(writer):
            if action == "download":
                run_download(
                    csv_file=csv_path,
                    canvas_token=params["token"],
                    base_url=params["base_url"],
                    output_folder=params["output_folder"],
                    file_id_column=params["file_id_column"],
                    filename_column=params["filename_column"],
                    progress_cb=lambda c, t, m: update_progress(job_id, c, t, m),
                )
            elif action == "upload":
                bulk_replace_ocr_files(
                    csv_file=csv_path,
                    canvas_token=params["token"],
                    base_url=params["base_url"],
                    ocr_folder=params["ocr_folder"],
                    file_id_col=params["file_id_column"],
                    ocr_path_col=params["filename_column"],
                    progress_cb=lambda c, t, m: update_progress(job_id, c, t, m),
                )
            else:
                print("Unknown action.")
    except Exception:
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job:
                job["log"] += "\n[ERROR] Unexpected failure:\n"
                job["log"] += traceback.format_exc()
    finally:
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if job:
                job["status"] = "done"
                job["message"] = "Finished"
        try:
            os.unlink(csv_path)
        except OSError:
            pass


PAGE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Canvas BulkFlow</title>
    <style>
      :root {
        --bg: #0f172a;
        --card: #111827;
        --accent: #22d3ee;
        --muted: #94a3b8;
        --text: #e2e8f0;
        --border: #1f2937;
      }
      * { box-sizing: border-box; }
      html, body { max-width: 100%; overflow-x: hidden; }
      body {
        margin: 0;
        font-family: "Segoe UI", "SF Pro Text", system-ui, sans-serif;
        color: var(--text);
        background:
          radial-gradient(800px 400px at 20% -10%, rgba(34,211,238,0.18), transparent),
          radial-gradient(700px 500px at 100% 0%, rgba(14,165,233,0.12), transparent),
          var(--bg);
        min-height: 100vh;
      }
      .wrap { max-width: 980px; margin: 0 auto; padding: 32px 20px 40px; }
      h1 { margin: 0 0 8px; font-size: 32px; letter-spacing: 0.4px; }
      .sub { color: var(--muted); margin-bottom: 20px; }
      .grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 20px; }
      .grid > * { min-width: 0; }
      .card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 18px; }
      .card h2 { margin: 0 0 12px; font-size: 16px; color: var(--accent); letter-spacing: 0.6px; text-transform: uppercase; }
      label { display: block; font-weight: 600; margin-bottom: 6px; }
      input[type="text"], input[type="file"] {
        width: 100%; padding: 10px 12px; border-radius: 10px;
        border: 1px solid #253041; background: #0b1220; color: var(--text);
        min-width: 0;
      }
      .row { margin-bottom: 12px; }
      .actions { margin-top: 10px; display: flex; gap: 10px; }
      button {
        padding: 10px 14px; border-radius: 10px; border: none;
        background: var(--accent); color: #001018; font-weight: 700; cursor: pointer;
      }
      button.secondary { background: #334155; color: var(--text); }
      button:disabled { opacity: 0.6; cursor: not-allowed; }
      .status { font-size: 14px; color: var(--muted); margin-bottom: 8px; }
      .bar {
        width: 100%; height: 14px; background: #0b1220; border-radius: 999px; overflow: hidden;
        border: 1px solid #243041;
      }
      .bar > div { height: 100%; width: 0%; background: linear-gradient(90deg, #22d3ee, #38bdf8); }
      pre {
        background: #0b1220; border: 1px solid #1f2937; padding: 12px; border-radius: 10px;
        height: 260px; overflow: auto; white-space: pre-wrap; color: #cbd5f5;
        word-break: break-word;
        overflow-wrap: anywhere;
      }
      .kpi { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px; color: var(--muted); }
      @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
        .actions { flex-wrap: wrap; }
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>Canvas BulkFlow</h1>
      <div class="sub">Upload the Ally CSV, then run Download or Upload. Abbyy OCR runs separately.</div>
      <div class="grid">
        <div class="card">
          <h2>Run</h2>
          <form id="jobForm" enctype="multipart/form-data">
            <div class="row">
              <label>Ally CSV file</label>
              <input type="file" name="csv_file" accept=".csv" required>
            </div>
            <div class="row">
              <label>Canvas base URL</label>
              <input type="text" name="base_url" value="{{ base_url }}">
            </div>
            <div class="row">
              <label>Canvas API token</label>
              <input type="text" name="token" value="{{ token }}" placeholder="CANVAS_API_TOKEN or paste token">
            </div>
            <div class="row">
              <label>Download folder</label>
              <input type="text" name="output_folder" value="{{ output_folder }}">
            </div>
            <div class="row">
              <label>OCRed folder</label>
              <input type="text" name="ocr_folder" value="{{ ocr_folder }}">
            </div>
            <div class="row">
              <label>File ID column</label>
              <input type="text" name="file_id_column" value="{{ file_id_column }}">
            </div>
            <div class="row">
              <label>Filename column</label>
              <input type="text" name="filename_column" value="{{ filename_column }}">
            </div>
            <div class="actions">
              <button type="button" id="downloadBtn">Download PDFs</button>
              <button type="button" id="uploadBtn" class="secondary">Upload OCRed PDFs</button>
            </div>
          </form>
        </div>
        <div class="card">
          <h2>Status</h2>
          <div class="status" id="statusText">Idle</div>
          <div class="bar"><div id="barFill"></div></div>
          <div class="kpi" style="margin-top:10px;">
            <div>Processed: <span id="processed">0</span></div>
            <div>Total: <span id="total">0</span></div>
          </div>
          <div style="margin-top: 14px; font-weight: 600;">Log</div>
          <pre id="logBox"></pre>
        </div>
      </div>
    </div>
    <script>
      const form = document.getElementById("jobForm");
      const downloadBtn = document.getElementById("downloadBtn");
      const uploadBtn = document.getElementById("uploadBtn");
      const statusText = document.getElementById("statusText");
      const barFill = document.getElementById("barFill");
      const processed = document.getElementById("processed");
      const total = document.getElementById("total");
      const logBox = document.getElementById("logBox");
      let currentJob = null;
      let pollTimer = null;
      let startInFlight = false;

      async function startJob(action) {
        if (currentJob || startInFlight) return;
        startInFlight = true;
        downloadBtn.disabled = true;
        uploadBtn.disabled = true;
        const formData = new FormData(form);
        formData.append("action", action);
        statusText.textContent = "Starting...";
        logBox.textContent = "";
        try {
          const resp = await fetch("/start", { method: "POST", body: formData });
          if (!resp.ok) {
            const msg = await resp.text();
            statusText.textContent = "Failed to start";
            logBox.textContent = msg;
            return;
          }
          const data = await resp.json();
          currentJob = data.job_id;
          startPolling();
        } catch (err) {
          statusText.textContent = "Failed to start";
          logBox.textContent = `Network error while starting job: ${err}`;
        } finally {
          startInFlight = false;
          if (!currentJob) {
            downloadBtn.disabled = false;
            uploadBtn.disabled = false;
          }
        }
      }

      async function pollStatus() {
        if (!currentJob) return;
        const resp = await fetch(`/status/${currentJob}`);
        if (!resp.ok) return;
        const data = await resp.json();

        statusText.textContent = data.message || data.status;
        processed.textContent = data.current || 0;
        total.textContent = data.total || 0;
        logBox.textContent = data.log || "";

        let pct = 0;
        if (data.total > 0) pct = Math.min(100, Math.round((data.current / data.total) * 100));
        barFill.style.width = `${pct}%`;

        if (data.status === "done") {
          stopPolling();
        }
      }

      function startPolling() {
        downloadBtn.disabled = true;
        uploadBtn.disabled = true;
        pollTimer = setInterval(pollStatus, 1000);
        pollStatus();
      }

      function stopPolling() {
        clearInterval(pollTimer);
        pollTimer = null;
        downloadBtn.disabled = false;
        uploadBtn.disabled = false;
        currentJob = null;
      }

      downloadBtn.addEventListener("click", () => startJob("download"));
      uploadBtn.addEventListener("click", () => startJob("upload"));
    </script>
  </body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    base_url = os.getenv("CANVAS_BASE_URL", DOWNLOAD_BASE_URL)
    token = os.getenv("CANVAS_API_TOKEN", "")
    return render_template_string(
        PAGE,
        token=token,
        base_url=base_url,
        output_folder=DEFAULT_OUTPUT_FOLDER,
        ocr_folder=DEFAULT_OCR_FOLDER,
        file_id_column="Id",
        filename_column="Name",
    )


@app.route("/start", methods=["POST"])
def start():
    csv_file = request.files.get("csv_file")
    if not csv_file:
        return "Missing CSV file.", 400

    action = request.form.get("action", "")
    if action not in ("download", "upload"):
        return "Invalid action.", 400

    token = request.form.get("token", "").strip() or os.getenv("CANVAS_API_TOKEN", "")
    if not token:
        return "Missing Canvas API token. Provide it in the form or CANVAS_API_TOKEN env var.", 400
    base_url = request.form.get("base_url", "").strip() or DOWNLOAD_BASE_URL
    output_folder = request.form.get("output_folder", "").strip() or DEFAULT_OUTPUT_FOLDER
    ocr_folder = request.form.get("ocr_folder", "").strip() or DEFAULT_OCR_FOLDER
    file_id_column = request.form.get("file_id_column", "").strip() or "Id"
    filename_column = request.form.get("filename_column", "").strip() or "Name"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(csv_file.read())
        tmp_path = tmp.name

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "message": "Queued",
            "current": 0,
            "total": 0,
            "log": "",
            "started_at": datetime.utcnow().isoformat() + "Z",
        }

    params = {
        "token": token,
        "base_url": base_url,
        "output_folder": output_folder,
        "ocr_folder": ocr_folder,
        "file_id_column": file_id_column,
        "filename_column": filename_column,
    }

    thread = threading.Thread(target=run_job, args=(job_id, action, tmp_path, params), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"status": "missing"}), 404
        return jsonify(job)


if __name__ == "__main__":
    import webbrowser

    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
