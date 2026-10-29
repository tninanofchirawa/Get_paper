"""
services/drive/mime.py - MIME type detection and compression helpers for Google Drive uploads.
Unified Academic Paper Harvester, Verifier & Notification Pipeline.
"""

import os
import gzip
import shutil
import logging
from typing import Tuple

logger = logging.getLogger("DriveMime")


def get_mime_and_stream(file_path: str, enable_gzip: bool = False) -> Tuple[str, str, bool]:
    """
    Determines MIME type and prepares optional gzip stream.
    Returns: (mime_type, actual_upload_path, is_compressed)
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        mime_type = "text/csv"
    elif ext in (".xlsx", ".xlsm"):
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif ext == ".pdf":
        mime_type = "application/pdf"
    elif ext == ".json":
        mime_type = "application/json"
    else:
        mime_type = "application/octet-stream"

    if enable_gzip:
        gz_path = f"{file_path}.gz"
        try:
            with open(file_path, "rb") as f_in, gzip.open(gz_path, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
            orig_size = os.path.getsize(file_path)
            gz_size = os.path.getsize(gz_path)
            logger.info(f"[DriveMime] Gzip compressed '{file_path}': {orig_size} -> {gz_size} bytes ({(1 - gz_size/orig_size)*100:.1f}% reduction)")
            return "application/gzip", gz_path, True
        except Exception as e:
            logger.warning(f"[DriveMime] Gzip compression failed: {e}. Falling back to uncompressed stream.")
            return mime_type, file_path, False

    return mime_type, file_path, False
