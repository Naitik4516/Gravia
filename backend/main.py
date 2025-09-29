from fastapi import FastAPI, Request, Depends
from fastapi.responses import StreamingResponse
import asyncio
import sys
from routers import chat, user, settings, integrations, knowledge
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from event_handler import event_queue
from contextlib import asynccontextmanager
from config import scheduler
from deps import user_exists
import os
from utils.logging_config import logger
from pydantic import BaseModel
import uvicorn

class NotificationActionRequest(BaseModel):
    id: str
    action: str

# Ensure Windows uses Proactor loop (required for asyncio subprocess APIs)
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost",
    "http://localhost:1420",
    "http://tauri.localhost"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat.router, dependencies=[Depends(user_exists)])
app.include_router(user.router)
app.include_router(settings.router)
app.include_router(integrations.router, dependencies=[Depends(user_exists)])
app.include_router(knowledge.router, dependencies=[Depends(user_exists)])


# Serve generated artifacts (e.g., code execution outputs) statically
# This exposes files under /artifacts/... so the frontend can display/download them.

os.makedirs("artifacts", exist_ok=True)
app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")


@app.post("/notification-action")
async def notification_action(request: NotificationActionRequest):
    """
    Handle notification actions from notifier.exe (e.g., alarm snooze)
    """
    logger.info(f"Received notification action: id={request.id}, action={request.action}")
    
    if request.action == "snooze":
        # Handle alarm snoozing
        from tools.alarms import handle_alarm_snooze
        result = await handle_alarm_snooze(request.id)
        return {"status": "success", "message": f"Alarm {request.id} snoozed", "result": result}
    elif request.action == "dismiss":
        # Handle alarm dismissal
        logger.info(f"Alarm {request.id} dismissed")
        return {"status": "success", "message": f"Alarm {request.id} dismissed"}
    else:
        logger.warning(f"Unknown action: {request.action}")
        return {"status": "error", "message": f"Unknown action: {request.action}"}


@app.get("/events")
async def sse_endpoint(request: Request):
    async def event_generator():
        while True:
            # Disconnect check
            if await request.is_disconnected():
                break

            try:
                # Wait for the next message
                message = await event_queue.get()
                yield message
            except asyncio.CancelledError:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5089)