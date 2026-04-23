import os

import dotenv
from aiohttp import web

from logging_config import logger

dotenv.load_dotenv()

HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8080"))


async def health_handler(request):
    return web.json_response({"status": "ok"})


async def run_health_server():
    health_app = web.Application()
    health_app.router.add_get("/health", health_handler)
    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HEALTH_PORT)
    await site.start()
    logger.info(f"Health check running on 0.0.0.0:{HEALTH_PORT}/health")
