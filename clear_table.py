import os

import dotenv
import requests

dotenv.load_dotenv()

BUCKET_URL = os.getenv("BUCKET_URL")
S3_KEY = os.getenv("S3_KEY")

with open("tickets.xlsx", "rb") as f:
    data = f.read()
resp = requests.put(
    f"{BUCKET_URL}/{S3_KEY}",
    data=data,
    headers={
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    },
)
