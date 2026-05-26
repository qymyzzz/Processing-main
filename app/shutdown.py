import os
import sys

import dotenv
import requests

from .logging_config import logger
from .s3_sync import s3_load_everything_sync

dotenv.load_dotenv()

BUCKET_URL = os.getenv("BUCKET_URL")
S3_KEY = os.getenv("S3_KEY")


def handle_shutdown():
    print("Shutdown signal received, uploading to S3...")
    s3_load_everything_sync()
    sys.exit(0)
