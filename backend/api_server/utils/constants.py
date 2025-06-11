import os

UPLOAD_DIR = "uploads"
ALLOWED_FILE_TYPES = ('.csv', '.xlsx', '.json')

os.makedirs(UPLOAD_DIR, exist_ok=True)
