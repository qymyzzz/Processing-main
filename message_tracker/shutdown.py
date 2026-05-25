import os
import sys

import dotenv
import requests

from .logging_config import logger
from .s3_load_last_messages import s3_load_last_messages_sync

dotenv.load_dotenv()


def handle_shutdown():
    print("Shutdown signal received, uploading to S3...")
    s3_load_last_messages_sync()
    sys.exit(0)
