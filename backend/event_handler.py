import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

event_queue: asyncio.Queue[str] = asyncio.Queue()
notification_queue: asyncio.Queue[str] = asyncio.Queue()


async def send_event(event: str):
    logger.info(f"Sending event: {event.strip()}")
    await event_queue.put(f"event: status\ndata: {event.strip()}\n\n")

async def send_notification(title: str, message: str | dict, type_: str = "info"):
    data = {
        "title": title,
        "message": message,
        "type": type_,   # e.g. info, warning, error, success
    }
    event = f"event: notification\ndata: {json.dumps(data)}\n\n"
    await notification_queue.put(event)

