import pandas as pd
import requests
import os
import re
import time
import argparse

# ========== Defaults ==========

DEFAULT_FILE_ID_COLUMN = "Id"
DEFAULT_FILENAME_COLUMN = "Name"
DEFAULT_BASE_URL = "https://usu.instructure.com"
DEFAULT_OUTPUT_FOLDER = r"C:\Canvas-BulkFlow\Downloads"

from canvas_bulkflow_config import load_env_file

load_env_file()

# ========== Utility Functions ==========
def sanitize_filename(name: str) -> str:
    """
    Removes characters not allowed on Windows file systems.
    """
    return re.sub(r'[\\/*?:"<>|]', "", name)

def load_filtered_df(csv_file, file_id_column, filename_column):
    df = pd.read_csv(csv_file)
    df = df[(df['Mime type'] == 'application/pdf') & (df['Scanned:1'] == 1)]
    df.info()

    # Find all filenames that appear more than once in the CSV
    duplicate_filenames_df = df[df.duplicated(subset=[filename_column], keep=False)]
    duplicate_names = set(duplicate_filenames_df[filename_column].unique())
    return df, duplicate_names


def run_download(
    csv_file,
    canvas_token,
    base_url=DEFAULT_BASE_URL,
    output_folder=DEFAULT_OUTPUT_FOLDER,
    file_id_column=DEFAULT_FILE_ID_COLUMN,
    filename_column=DEFAULT_FILENAME_COLUMN,
    progress_cb=None,
):
    token = canvas_token or os.getenv("CANVAS_API_TOKEN", "")
    if not token:
        print("Canvas API token is required. Set CANVAS_API_TOKEN or provide it in the UI.")
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }

    os.makedirs(output_folder, exist_ok=True)

    df, duplicate_names = load_filtered_df(csv_file, file_id_column, filename_column)

    total_rows = len(df)
    processed_rows = 0

    # We'll keep track of:
    # 1) files that were skipped due to duplication
    # 2) files that were downloaded
    skipped_duplicates = []
    downloaded_files = []

    for index, row in df.iterrows():
        processed_rows += 1
        if progress_cb:
            progress_cb(processed_rows, total_rows, f"Processing row {index}...")
        file_id = row[file_id_column]
        file_name = sanitize_filename(str(row[filename_column]))

        # Skip if no file ID
        if pd.isna(file_id):
            print(f"[Row {index}] Missing File ID. Skipping.")
            continue

        # If this file name is in the duplicates set, skip *all* instances
        if file_name in duplicate_names:
            skipped_duplicates.append((file_id, file_name))
            print(f"[Row {index}] Skipping ALL duplicates named '{file_name}' (File ID: {file_id}).")
            continue

        # 1. Fetch file metadata from Canvas API
        file_api_url = f"{base_url}/api/v1/files/{int(file_id)}"
        meta_resp = requests.get(file_api_url, headers=headers)
        if meta_resp.status_code != 200:
            print(f"[Row {index}] Failed to retrieve metadata for file ID {file_id} (Status: {meta_resp.status_code}). Skipping.")
            continue

        file_info = meta_resp.json()
        download_url = file_info.get("url")
        expected_size = file_info.get("size")

        if not download_url:
            print(f"[Row {index}] No download URL found for file ID {file_id}. Skipping.")
            continue

        # 2. Download the file
        print(f"[Row {index}] Downloading {file_name} from {download_url}")
        download_resp = requests.get(download_url, headers=headers, stream=True)
        if download_resp.status_code != 200:
            print(f"[Row {index}] Failed to download {file_name} (Status: {download_resp.status_code}).")
            continue

        # Check the response Content-Type for debugging
        content_type = download_resp.headers.get("Content-Type", "")
        if "application/pdf" not in content_type.lower():
            print(f"[Row {index}] Warning: {file_name} returned unexpected Content-Type: {content_type}")

        # 3. Save the file to disk
        filepath = os.path.join(output_folder, file_name)
        with open(filepath, "wb") as f:
            for chunk in download_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        download_resp.close()

        # 4. Verify file size
        actual_size = os.path.getsize(filepath)
        if expected_size and actual_size < expected_size:
            print(f"[Row {index}] Downloaded {file_name} is smaller than expected "
                  f"(Expected: {expected_size} bytes, Got: {actual_size} bytes).")
        else:
            print(f"[Row {index}] Downloaded {file_name} ({actual_size} bytes) successfully.")

        downloaded_files.append((file_id, file_name))

        # Optional: short pause to reduce chance of rate-limiting
        time.sleep(1)

    # Final summary
    print("\n=== DOWNLOAD SUMMARY ===")
    print(f"Downloaded: {len(downloaded_files)} files.")
    if skipped_duplicates:
        print(f"Skipped {len(skipped_duplicates)} files due to name duplication:")
        for (dup_id, dup_name) in skipped_duplicates:
            print(f"  - File ID: {dup_id}, Name: {dup_name}")
    else:
        print("No duplicates were skipped.")

# ========== Script Entry Point ==========
def main():
    parser = argparse.ArgumentParser(description="Download scanned PDFs from Canvas based on CSV.")
    parser.add_argument("--csv", required=True, help="Path to the Ally CSV file")
    parser.add_argument("--token", default=os.getenv("CANVAS_API_TOKEN", ""), help="Canvas API token")
    parser.add_argument("--base-url", default=os.getenv("CANVAS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--output-folder", default=DEFAULT_OUTPUT_FOLDER)
    parser.add_argument("--file-id-column", default=DEFAULT_FILE_ID_COLUMN)
    parser.add_argument("--filename-column", default=DEFAULT_FILENAME_COLUMN)
    args = parser.parse_args()

    run_download(
        csv_file=args.csv,
        canvas_token=args.token,
        base_url=args.base_url,
        output_folder=args.output_folder,
        file_id_column=args.file_id_column,
        filename_column=args.filename_column,
    )


if __name__ == "__main__":
    main()
