import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from contextlib import redirect_stdout, redirect_stderr

from canvas_bulk_download import (
    run_download,
    DEFAULT_BASE_URL as DOWNLOAD_BASE_URL,
    DEFAULT_OUTPUT_FOLDER,
)
from canvas_bulk_upload import (
    bulk_replace_ocr_files,
    DEFAULT_BASE_URL as UPLOAD_BASE_URL,
    DEFAULT_OCR_FOLDER,
)


class QueueWriter:
    def __init__(self, q):
        self.q = q

    def write(self, msg):
        if msg:
            self.q.put(msg)

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Canvas BulkFlow")
        self.geometry("900x700")
        self.minsize(820, 620)

        self.log_queue = queue.Queue()
        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(container, text="Canvas BulkFlow", font=("Segoe UI", 18, "bold"))
        header.pack(anchor="w", pady=(0, 8))

        self.csv_path = tk.StringVar()
        self.token = tk.StringVar(value=os.getenv("CANVAS_API_TOKEN", ""))
        self.base_url = tk.StringVar(value=os.getenv("CANVAS_BASE_URL", DOWNLOAD_BASE_URL))
        self.output_folder = tk.StringVar(value=DEFAULT_OUTPUT_FOLDER)
        self.ocr_folder = tk.StringVar(value=DEFAULT_OCR_FOLDER)
        self.file_id_column = tk.StringVar(value="Id")
        self.filename_column = tk.StringVar(value="Name")
        self.show_token = tk.BooleanVar(value=False)

        form = ttk.Frame(container)
        form.pack(fill=tk.X, pady=(0, 8))

        self._row(form, 0, "Ally CSV file", self.csv_path, browse=self._browse_csv)
        self._row(form, 1, "Canvas API token", self.token, show="*", toggle=self._toggle_token)
        self._row(form, 2, "Canvas base URL", self.base_url)
        self._row(form, 3, "Download folder", self.output_folder, browse=self._browse_output)
        self._row(form, 4, "OCRed folder", self.ocr_folder, browse=self._browse_ocr)
        self._row(form, 5, "File ID column", self.file_id_column)
        self._row(form, 6, "Filename column", self.filename_column)

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(4, 12))

        self.download_btn = ttk.Button(actions, text="Download PDFs", command=self._download_clicked)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.upload_btn = ttk.Button(actions, text="Upload OCRed PDFs", command=self._upload_clicked)
        self.upload_btn.pack(side=tk.LEFT)

        log_label = ttk.Label(container, text="Log")
        log_label.pack(anchor="w")

        self.log_text = tk.Text(container, height=18, wrap="word", state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=True)

        tip = ttk.Label(
            container,
            text="Tip: Abbyy OCR runs separately. Use the same CSV for both steps.",
            foreground="#666666",
        )
        tip.pack(anchor="w", pady=(6, 0))

    def _row(self, parent, row, label, var, browse=None, show=None, toggle=None):
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=4)

        entry = ttk.Entry(parent, textvariable=var, show=show)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=4)
        if var is self.token:
            self.token_entry = entry

        parent.grid_columnconfigure(1, weight=1)

        if browse:
            btn = ttk.Button(parent, text="Browse", command=browse)
            btn.grid(row=row, column=2, sticky="ew")

        if toggle:
            chk = ttk.Checkbutton(parent, text="Show", variable=self.show_token, command=toggle)
            chk.grid(row=row, column=3, sticky="w", padx=(6, 0))

    def _toggle_token(self):
        show = "" if self.show_token.get() else "*"
        if hasattr(self, "token_entry"):
            self.token_entry.config(show=show)

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="Select Ally CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.csv_path.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Download Folder")
        if path:
            self.output_folder.set(path)

    def _browse_ocr(self):
        path = filedialog.askdirectory(title="Select OCRed Folder")
        if path:
            self.ocr_folder.set(path)

    def _download_clicked(self):
        if not self._validate_common():
            return
        self._run_task(self._do_download)

    def _upload_clicked(self):
        if not self._validate_common():
            return
        self._run_task(self._do_upload)

    def _validate_common(self):
        if not self.csv_path.get():
            messagebox.showerror("Missing CSV", "Please select the Ally CSV file.")
            return False
        if not os.path.exists(self.csv_path.get()):
            messagebox.showerror("CSV not found", "The selected CSV file does not exist.")
            return False
        return True

    def _run_task(self, func):
        self.download_btn.config(state="disabled")
        self.upload_btn.config(state="disabled")
        thread = threading.Thread(target=func, daemon=True)
        thread.start()

    def _do_download(self):
        self._log("Starting download...\n")
        writer = QueueWriter(self.log_queue)
        try:
            with redirect_stdout(writer), redirect_stderr(writer):
                run_download(
                    csv_file=self.csv_path.get(),
                    canvas_token=self.token.get().strip(),
                    base_url=self.base_url.get().strip() or DOWNLOAD_BASE_URL,
                    output_folder=self.output_folder.get().strip() or DEFAULT_OUTPUT_FOLDER,
                    file_id_column=self.file_id_column.get().strip() or "Id",
                    filename_column=self.filename_column.get().strip() or "Name",
                )
        except Exception as exc:
            self._log(f"\n[ERROR] {exc}\n")
        finally:
            self._log("\nDownload finished.\n")
            self._enable_buttons()

    def _do_upload(self):
        self._log("Starting upload...\n")
        writer = QueueWriter(self.log_queue)
        try:
            with redirect_stdout(writer), redirect_stderr(writer):
                bulk_replace_ocr_files(
                    csv_file=self.csv_path.get(),
                    canvas_token=self.token.get().strip(),
                    base_url=self.base_url.get().strip() or UPLOAD_BASE_URL,
                    ocr_folder=self.ocr_folder.get().strip() or DEFAULT_OCR_FOLDER,
                    file_id_col=self.file_id_column.get().strip() or "Id",
                    ocr_path_col=self.filename_column.get().strip() or "Name",
                )
        except Exception as exc:
            self._log(f"\n[ERROR] {exc}\n")
        finally:
            self._log("\nUpload finished.\n")
            self._enable_buttons()

    def _enable_buttons(self):
        self.download_btn.config(state="normal")
        self.upload_btn.config(state="normal")

    def _log(self, text):
        self.log_queue.put(text)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert(tk.END, msg)
                self.log_text.see(tk.END)
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)


if __name__ == "__main__":
    app = App()
    app.mainloop()
