import os
import time
import requests
import pandas as pd
import argparse

# -------------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://usu.instructure.com"
DEFAULT_OCR_FOLDER = r"C:\Canvas-BulkFlow\Downloads\OCRed"

from canvas_bulkflow_config import load_env_file

load_env_file()

# -------------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------------

def get_file_metadata(file_id, headers, base_url):
    url = f"{base_url}/api/v1/files/{file_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"[get_file_metadata] Failed for file_id={file_id}. Status {resp.status_code}: {resp.text}")
        return None

def get_folder_metadata(folder_id, headers, base_url):
    url = f"{base_url}/api/v1/folders/{folder_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"[get_folder_metadata] Failed for folder_id={folder_id}. Status {resp.status_code}: {resp.text}")
        return None

def overwrite_file_in_canvas(course_id, folder_id, local_file_path, filename, headers, base_url):
    if not os.path.exists(local_file_path):
        print(f"[overwrite_file_in_canvas] Local file not found: {local_file_path}")
        return False

    file_size = os.path.getsize(local_file_path)
    content_type = 'application/pdf'

    # 1) Initiate the upload
    initiate_url = f"{base_url}/api/v1/courses/{course_id}/files"
    payload = {
        'name': filename,
        'parent_folder_id': folder_id,
        'on_duplicate': 'overwrite',
        'size': file_size,
        'content_type': content_type
    }

    print(f"[Initiate] POST {initiate_url} with payload={payload}")
    init_resp = requests.post(initiate_url, headers=headers, data=payload)
    print("[Initiate] Status:", init_resp.status_code)
    print("[Initiate] Body:", init_resp.text)

    if init_resp.status_code not in (200, 201):
        print(f"Failed to initiate upload for '{filename}'.")
        return False

    upload_info = init_resp.json()
    upload_url = upload_info.get('upload_url')
    upload_params = upload_info.get('upload_params')
    if not upload_url or not upload_params:
        print("[Initiate] Missing 'upload_url' or 'upload_params' in initiation response.")
        return False

    # 2) Perform the actual file upload
    with open(local_file_path, 'rb') as f:
        files_data = {
            'file': (filename, f, content_type)
        }
        upload_resp = requests.post(upload_url, data=upload_params, files=files_data)

    print("[Upload] Status:", upload_resp.status_code)
    print("[Upload] Body:", upload_resp.text)

    if upload_resp.status_code in [200, 201]:
        print(f"Successfully replaced file with '{filename}' (status={upload_resp.status_code}).")
        return True
    elif upload_resp.status_code == 302:
        # Handle possible redirect
        redirect_url = upload_resp.headers.get('Location')
        if redirect_url:
            final_resp = requests.get(redirect_url, headers=headers)
            print("[Redirect] Status:", final_resp.status_code)
            print("[Redirect] Body:", final_resp.text)
            if final_resp.status_code in [200, 201]:
                print(f"Successfully replaced file with '{filename}' (after redirect).")
                return True
        print("Redirect failed or missing location header.")
        return False
    else:
        print(f"File upload step failed. Status {upload_resp.status_code}")
        return False

# -------------------------------------------------------------------------------
# Bulk Replacement Function with Logging
# -------------------------------------------------------------------------------

def bulk_replace_ocr_files(
    csv_file,
    canvas_token,
    base_url=DEFAULT_BASE_URL,
    ocr_folder=DEFAULT_OCR_FOLDER,
    file_id_col="File_ID",
    ocr_path_col="OCR_File_Path",
    progress_cb=None,
):
    """
    Reads a CSV file containing:
      - A column with Canvas File IDs (file_id_col)
      - A column with the OCRed PDF's filename (ocr_path_col); the file is located in the fixed 'ocr_folder'
    
    Then overwrites each file in Canvas with the OCRed version and prints a summary log.
    """
    token = canvas_token or os.getenv("CANVAS_API_TOKEN", "")
    if not token:
        print("Canvas API token is required. Set CANVAS_API_TOKEN or provide it in the UI.")
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }

    df = pd.read_csv(csv_file)
    total_rows = len(df)
    success_count = 0
    failure_count = 0
    skipped_count = 0

    total_rows = len(df)
    processed_rows = 0

    for idx, row in df.iterrows():
        processed_rows += 1
        if progress_cb:
            progress_cb(processed_rows, total_rows, f"Processing row {idx}...")
        file_id = row.get(file_id_col)
        file_name_from_csv = row.get(ocr_path_col)
        # Build full local file path by joining the OCR folder with the filename from the CSV
        local_file_path = os.path.join(ocr_folder, file_name_from_csv) if pd.notna(file_name_from_csv) else None

        if not file_id or pd.isna(file_id):
            print(f"[Row {idx}] Missing file_id. Skipping.")
            skipped_count += 1
            continue
        if not local_file_path or not os.path.exists(local_file_path):
            print(f"[Row {idx}] Local file path missing or invalid: {local_file_path}. Skipping.")
            skipped_count += 1
            continue

        # (A) Get file metadata
        file_info = get_file_metadata(file_id, headers, base_url)
        if not file_info:
            print(f"[Row {idx}] Failed to get metadata for file_id={file_id}. Skipping.")
            skipped_count += 1
            continue

        folder_id = file_info.get('folder_id')
        old_filename = file_info.get('display_name')

        # (B) Get folder metadata to determine course_id
        folder_info = get_folder_metadata(folder_id, headers, base_url)
        if not folder_info:
            print(f"[Row {idx}] Failed to get folder info for folder_id={folder_id}. Skipping.")
            skipped_count += 1
            continue

        course_id = folder_info.get('context_id')
        context_type = folder_info.get('context_type')
        if str(context_type).lower() != 'course':
            print(f"[Row {idx}] Not a course folder (context_type={context_type}). Skipping.")
            skipped_count += 1
            continue

        # (C) Overwrite the file in Canvas
        print(f"[Row {idx}] Overwriting file_id={file_id} with local file: {local_file_path}")
        success = overwrite_file_in_canvas(course_id, folder_id, local_file_path, old_filename, headers, base_url)
        if success:
            print(f"[Row {idx}] Successfully replaced file_id={file_id}.")
            success_count += 1
        else:
            print(f"[Row {idx}] Failed to replace file_id={file_id}.")
            failure_count += 1

        # Optional: Pause to avoid rate-limiting
        time.sleep(1)

    # Final summary log
    print("\n=== UPLOAD SUMMARY ===")
    print(f"Total rows in CSV: {total_rows}")
    print(f"Files successfully replaced: {success_count}")
    print(f"Files failed to replace: {failure_count}")
    print(f"Files skipped: {skipped_count}")

# -------------------------------------------------------------------------------
# Main / Example
# -------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Replace Canvas files with OCRed versions based on CSV.")
    parser.add_argument("--csv", required=True, help="Path to the CSV file")
    parser.add_argument("--token", default=os.getenv("CANVAS_API_TOKEN", ""), help="Canvas API token")
    parser.add_argument("--base-url", default=os.getenv("CANVAS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--ocr-folder", default=DEFAULT_OCR_FOLDER)
    parser.add_argument("--file-id-column", default="Id")
    parser.add_argument("--filename-column", default="Name")
    args = parser.parse_args()

    bulk_replace_ocr_files(
        csv_file=args.csv,
        canvas_token=args.token,
        base_url=args.base_url,
        ocr_folder=args.ocr_folder,
        file_id_col=args.file_id_column,
        ocr_path_col=args.filename_column,
    )


if __name__ == "__main__":
    main()
