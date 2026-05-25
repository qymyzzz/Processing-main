import threading
from collections import deque
import os
from dotenv import load_dotenv
from telegram.ext import Application
import json

from .get_data import _get_last_messages_path

from .logging_config import logger
import urllib.request
import requests

_lock = threading.Lock()

load_dotenv()

STORAGE_FILE = os.getenv("STORAGE_FILE")
BUCKET_URL = os.getenv("BUCKET_URL")


def init_last_messages():
    url = f"{BUCKET_URL}/{STORAGE_FILE}"
    try:
        urllib.request.urlretrieve(url, _get_last_messages_path())
        logger.info(f"{STORAGE_FILE} downloaded from S3")
    except Exception as e:
        logger.warning(f"Failed to download {STORAGE_FILE} from S3: {e}")


async def s3_load_last_messages(app: Application) -> None:
    with _lock:
        filepath = _get_last_messages_path()
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)

    payload = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    response = requests.put(
        f"{BUCKET_URL}/{STORAGE_FILE}",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    logger.info("Saved last messages to S3")


def s3_load_last_messages_sync():
    with _lock:
        filepath = _get_last_messages_path()
        with open(filepath, "r", encoding="utf-8") as f:
            raw = json.load(f)

    payload = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    response = requests.put(
        f"{BUCKET_URL}/{STORAGE_FILE}",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    logger.info("Saved last messages to S3")
