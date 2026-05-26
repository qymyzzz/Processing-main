import threading
from collections import deque
import os
from dotenv import load_dotenv
from telegram.ext import Application
import json
from .logging_config import logger
import urllib.request
import requests

from .ticket_system.ticket_store import s3_load_tickets, s3_load_tickets_sync
from .ticket_system.message_history import s3_load_messages, s3_load_messages_sync
from .message_tracker.s3_load_last_messages import (
    s3_load_last_messages,
    s3_load_last_messages_sync,
)
import urllib.request
import requests


async def s3_load_everything(app: Application) -> None:
    await s3_load_tickets(app=app)
    await s3_load_messages(app=app)
    await s3_load_last_messages(app=app)
    logger.info("Saved everything to S3")


def s3_load_everything_sync():
    s3_load_tickets_sync()
    s3_load_messages_sync()
    s3_load_last_messages_sync()
    logger.info("Saved everything to S3")
