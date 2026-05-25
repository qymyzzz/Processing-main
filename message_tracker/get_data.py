import os
import json
from dotenv import load_dotenv

load_dotenv()

STORAGE_FILE = os.getenv("STORAGE_FILE")


def _get_data_dir() -> str:
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _get_last_messages_path() -> str:
    return os.path.join(_get_data_dir(), STORAGE_FILE)
