import os
import sys

import dotenv
import requests

from .logging_config import logger
from .ticket_store import s3_load_tickets_sync
from .message_history import s3_load_messages_sync

dotenv.load_dotenv()

BUCKET_URL = os.getenv("BUCKET_URL")
S3_KEY = os.getenv("S3_KEY")


def handle_shutdown():
    print("Shutdown signal received, uploading to S3...")
    s3_load_tickets_sync()
    s3_load_messages_sync()
    sys.exit(0)
