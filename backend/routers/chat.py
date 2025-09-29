import asyncio
import base64
import datetime
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agno.agent import RunEvent
from agno.db.base import SessionType
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from agent import AGENTS, get_agent_by_key, root_agent
from config import GEMINI_API_KEY
from event_handler import send_event
from utils.data_handler import settings, user
from utils.file_handler import extract_media_from_text, process_file
from utils.logging_config import logger
from utils.voice.asr_service import TranscriptionEvent, asr_manager
from utils.voice.tts import stop_tts, synthesize_text

router = APIRouter(tags=["chat"], prefix="/chat")

user_id = str(user.get("id", "default_user"))


@router.post("/cancel")
async def cancel_run(payload: Dict[str, Any]):
    run_id = payload.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="Missing run_id")
    try:
        cancel_fn = getattr(root_agent, "cancel_run", None)
        if cancel_fn is None:
            raise HTTPException(
                status_code=501,
                detail="Run cancellation not supported in this environment",
            )
        res = cancel_fn(run_id)
        if asyncio.iscoroutine(res):
            await res
        return {"cancelled": True, "run_id": run_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dataclass
class SessionContext:
    websocket: WebSocket
    session_id: Optional[str]
    new_session: bool = False
    current_task: Optional[asyncio.Task] = None
    current_run_id: Optional[str] = None
    auto_speak: bool = False
    asr_session_key: str = ""
    closing: bool = False

    def cancel_stream_task(self):
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    raw_session_id = websocket.query_params.get("session_id")
    normalized_session_id = (
        None
        if raw_session_id is None
        or str(raw_session_id).strip().lower() in {"", "null", "undefined"}
        else str(raw_session_id).strip()
    )

    ctx = SessionContext(
        websocket=websocket,
        session_id=normalized_session_id,
        auto_speak=bool(settings.get("auto_speak")),
        asr_session_key=f"ws-{id(websocket)}",
    )

    # Ensure root_agent knows about provided session id immediately (some internal
    # operations / tools may rely on root_agent.session_id being set even though
    # we pass session_id explicitly to agent.arun)
    try:
        if ctx.session_id:
            root_agent.session_id = ctx.session_id
    except Exception:
        pass

    artifacts_path = Path(__file__).parent.parent / "artifacts"

    async def check_and_send_artifacts(start_time_dt: datetime.datetime):
        if not artifacts_path.exists():
            return

        start_timestamp = start_time_dt.timestamp()

        for file_path in artifacts_path.rglob("*"):
            if file_path.is_file():
                try:
                    # Check both modification time and creation time for robustness
                    file_stat = file_path.stat()
                    mod_time = file_stat.st_mtime
                    try:
                        # ctime is creation time on Windows
                        create_time = file_stat.st_ctime
                    except AttributeError:
                        create_time = mod_time  # Fallback for other OS

                    if mod_time > start_timestamp or create_time > start_timestamp:
                        logger.info(f"Detected new/updated artifact: {file_path}")
                        try:
                            await ctx.websocket.send_json(
                                {
                                    "type": "file_artifact",
                                    "file": {
                                        "name": file_path.name,
                                        "path": str(file_path),
                                    },
                                }
                            )
                        except Exception as e:
                            logger.error(f"Error sending artifact {file_path}: {e}")

                except (OSError, FileNotFoundError) as e:
                    logger.error(f"Error accessing file {file_path}: {e}")

    logger.info(f"WebSocket connected, session_id: {ctx.session_id}")

    async def ensure_session_created():
        if not ctx.session_id or not str(ctx.session_id).strip():
            ctx.session_id = str(uuid4())
            root_agent.session_id = ctx.session_id
            ctx.new_session = True
            await ctx.websocket.send_json(
                {"type": "session_created", "session_id": ctx.session_id}
            )

    async def generate_title(first_query: str, response_text: str):
        try:
            asyncio.create_task(
                generate_session_title(
                    session_id=ctx.session_id or "",
                    first_query=first_query,
                    response=response_text,
                )
            )
            ctx.new_session = False
        except Exception:
            pass

    async def stream_agent(
        query: str,
        agent_key: str,
        images=None,
        audios=None,
        videos=None,
        files=None,
    ):
        await ensure_session_created()
        start_time = datetime.datetime.now()
        logger.debug(f"Session id = {ctx.session_id}")
        agent = get_agent_by_key(agent_key)

        async def run():
            try:
                logger.debug(f"Starting agent run for query: {query}")
                retry_performed = False
                while True:
                    try:
                        async for ev in agent.arun(
                            input=query,
                            user_id=user_id,
                            session_id=ctx.session_id,
                            stream=True,
                            stream_intermediate_steps=True,
                            images=images,
                            audios=audios,
                            videos=videos,
                            files=files,
                        ):
                            rid = getattr(ev, "run_id", None)
                            if isinstance(rid, str):
                                ctx.current_run_id = rid
                            event_name = getattr(ev, "event", None)
                            if event_name == RunEvent.run_content:
                                part = ev.content
                                if part and part.strip():
                                    await ctx.websocket.send_json(
                                        {"type": "message_chunk", "message": part}
                                    )

                                    if ctx.auto_speak:
                                        try:
                                            speak_res = synthesize_text(
                                                ctx.websocket, part
                                            )
                                            if asyncio.iscoroutine(speak_res):
                                                asyncio.create_task(speak_res)
                                        except Exception:
                                            pass
                                # Attempt to stream images if present on the event (guarded for safety)
                                try:
                                    img = getattr(ev, "image", None)
                                    if img and getattr(img, "content", None):
                                        mime = (
                                            getattr(img, "mime_type", "image/png")
                                            or "image/png"
                                        )
                                        content_bytes = (
                                            getattr(img, "content", b"") or b""
                                        )
                                        if (
                                            isinstance(
                                                content_bytes, (bytes, bytearray)
                                            )
                                            and content_bytes
                                        ):
                                            b64_data = base64.b64encode(
                                                content_bytes
                                            ).decode("utf-8")
                                            await ctx.websocket.send_json(
                                                {
                                                    "type": "image",
                                                    "data": f"data:{mime};base64,{b64_data}",
                                                }
                                            )
                                except Exception:
                                    # Non-fatal; continue streaming text
                                    pass
                            elif event_name == RunEvent.reasoning_step:
                                await ctx.websocket.send_json(
                                    {"type": "reasoning_step", "message": ev.content}
                                )
                            elif event_name == RunEvent.reasoning_started:
                                await send_event("Thinking...")
                            elif event_name == RunEvent.reasoning_completed:
                                await send_event("Done thinking.")
                            elif event_name == RunEvent.run_completed:
                                ctx.current_run_id = None
                                await check_and_send_artifacts(start_time)
                                await send_event("clear")

                                try:
                                    await ctx.websocket.send_json(
                                        {"type": "message_end"}
                                    )
                                except Exception:
                                    pass

                                if ctx.new_session:
                                    await generate_title(
                                        first_query=query,
                                        response_text=ev.content or "",
                                    )
                            elif event_name == RunEvent.memory_update_completed:
                                await send_event("Memory updated.")
                            elif event_name == RunEvent.tool_call_started:
                                await ctx.websocket.send_json(
                                    {"type": "tool_call_started", "tool": ev.content}
                                )
                            elif event_name == RunEvent.tool_call_completed:
                                await ctx.websocket.send_json(
                                    {"type": "tool_call_completed", "tool": ev.content}
                                )
                            elif event_name == RunEvent.run_error:
                                ctx.current_run_id = None
                                await ctx.websocket.send_json(
                                    {"type": "error", "message": ev.content}
                                )
                                await send_event("error")
                                try:
                                    await ctx.websocket.send_json(
                                        {"type": "message_end"}
                                    )
                                except Exception:
                                    pass
                        break  # normal completion
                    except Exception as inner_e:
                        err_text = str(inner_e)
                        # Retry once if session_id missing / invalid
                        if (
                            "no session_id" in err_text.lower()
                            or "session_id" in err_text.lower()
                        ) and not retry_performed:
                            old_sid = ctx.session_id
                            ctx.session_id = ctx.session_id or str(uuid4())
                            try:
                                root_agent.session_id = ctx.session_id
                            except Exception:
                                pass
                            try:
                                await ctx.websocket.send_json(
                                    {
                                        "type": "session_created",
                                        "session_id": ctx.session_id,
                                    }
                                )
                            except Exception:
                                pass
                            logger.warning(
                                f"Retrying agent run due to session id issue. Old={old_sid} New={ctx.session_id}"
                            )
                            retry_performed = True
                            await asyncio.sleep(0)  # yield control
                            continue
                        raise
            except Exception as e:
                error_str = str(e)
                logger.error(f"Agent execution error: {error_str}")
                # Provide user-friendly error messages
                if (
                    "quota exceeded" in error_str.lower()
                    or "resource_exhausted" in error_str.lower()
                ):
                    user_message = "API quota exceeded. Please check your Gemini API billing and usage limits."
                elif "chunk too big" in error_str.lower():
                    user_message = "Your input is too large. Please try with shorter text or fewer images."
                elif "429" in error_str or "too many requests" in error_str.lower():
                    user_message = (
                        "Too many requests. Please wait a moment and try again."
                    )
                elif "invalid_argument" in error_str.lower():
                    user_message = (
                        "Invalid request format. Please try rephrasing your query."
                    )
                else:
                    user_message = "An error occurred while processing your request. Please try again."
                ctx.current_run_id = None
                await ctx.websocket.send_json(
                    {"type": "error", "message": user_message}
                )
                await send_event("error")
                try:
                    await ctx.websocket.send_json({"type": "message_end"})
                except Exception:
                    pass

        ctx.current_task = asyncio.create_task(run())
        await ctx.websocket.send_json({"type": "event", "message": "processing_query"})

    async def ensure_asr_started():
        if asr_manager.get(ctx.asr_session_key):
            return

        async def handle_asr_event(ev: TranscriptionEvent):
            if ev.type == "partial":
                await ctx.websocket.send_json(
                    {"type": "transcription_partial", "message": ev.text}
                )
            elif ev.type == "final":
                await ctx.websocket.send_json(
                    {"type": "transcription_final", "message": ev.text}
                )
                # if ev.text.strip():
                #     async with asr_submit_lock:
                #         await stream_agent(query=ev.text, agent_key="general")
            elif ev.type == "error":
                await ctx.websocket.send_json(
                    {"type": "transcription_error", "error": ev.text}
                )
            elif ev.type == "status":
                await ctx.websocket.send_json(
                    {"type": "transcription_status", "status": ev.text}
                )
                if ev.text == "no_speech_timeout":
                    await asr_manager.close_session(ctx.asr_session_key)

        await asr_manager.start_session(
            session_key=ctx.asr_session_key, on_event=handle_asr_event
        )
        await ctx.websocket.send_json(
            {"type": "transcription_status", "status": "listening"}
        )

    async def stop_listening():
        await asr_manager.close_session(ctx.asr_session_key)
        await ctx.websocket.send_json(
            {"type": "transcription_status", "status": "stopped"}
        )

    async def cancel_current(reason: str = "interrupted"):
        ctx.cancel_stream_task()
        try:
            if ctx.current_run_id:
                # Best-effort run cancel: obtain an agent from root_agent mapping if needed
                cancel_fn = getattr(root_agent, "cancel_run", None)
                if cancel_fn:
                    res = cancel_fn(ctx.current_run_id)
                    if asyncio.iscoroutine(res):
                        await res
        except Exception:
            pass
        finally:
            ctx.current_run_id = None
        try:
            await stop_tts()
        except Exception:
            pass
        try:
            await asr_manager.close_session(ctx.asr_session_key)
        except Exception:
            pass
        await ctx.websocket.send_json(
            {"type": "event", "message": f"Response {reason}."}
        )

    try:
        while True:
            data = await ctx.websocket.receive_json()
            msg_type = isinstance(data, dict) and data.get("type")
            if msg_type == "interrupt":
                await cancel_current("manually interrupted")
                continue
            if msg_type == "speak":
                await synthesize_text(ctx.websocket, data["text"])
                continue
            if msg_type == "stop_speaking":
                await stop_tts()
                # Always send tts_complete so UI can update
                await ctx.websocket.send_json(
                    {"type": "tts_complete", "message": "TTS stopped."}
                )
                continue
            if msg_type == "start_listening":
                await ensure_asr_started()
                continue
            if msg_type == "stop_listening":
                await stop_listening()
                continue

            # Standard query path
            if "query" in data:
                query_text = data["query"]
                images = audios = videos = files = None
                temp_files_to_clean = []
                try:
                    if "files" in data:
                        raw_files = data.get("files") or []
                        file_paths = []

                        for f in raw_files:
                            if f.get("path"):
                                file_paths.append(f["path"])
                            elif f.get("data_b64"):
                                try:
                                    file_data = base64.b64decode(f["data_b64"])
                                    # Create a temporary file
                                    with tempfile.NamedTemporaryFile(
                                        delete=False, suffix=f.get("name", "")
                                    ) as temp_f:
                                        temp_f.write(file_data)
                                        file_paths.append(temp_f.name)
                                        temp_files_to_clean.append(temp_f.name)
                                except (base64.binascii.Error, IOError) as e:
                                    await ctx.websocket.send_json(
                                        {
                                            "type": "error",
                                            "message": f"Error processing file: {e}",
                                        }
                                    )
                                    continue
                            elif f.get("data_url"):
                                # Handle data URLs directly without creating temp files
                                try:
                                    from utils.file_handler import (
                                        create_media_from_data_url,
                                    )

                                    logger.info(
                                        f"Processing data URL: {f['data_url'][:50]}..."
                                    )
                                    media_obj = create_media_from_data_url(
                                        f["data_url"]
                                    )

                                    # Add to appropriate media list based on type
                                    if hasattr(media_obj, "__class__"):
                                        media_type = (
                                            media_obj.__class__.__name__.lower()
                                        )
                                        logger.info(
                                            f"Created {media_type} object from data URL"
                                        )
                                        if media_type == "image":
                                            images = (images or []) + [media_obj]
                                        elif media_type == "audio":
                                            audios = (audios or []) + [media_obj]
                                        elif media_type == "video":
                                            videos = (videos or []) + [media_obj]
                                        elif media_type == "file":
                                            files = (files or []) + [media_obj]
                                except Exception as e:
                                    logger.error(f"Error processing data URL: {e}")
                                    await ctx.websocket.send_json(
                                        {
                                            "type": "error",
                                            "message": f"Error processing data URL: {e}",
                                        }
                                    )
                                    continue

                        if file_paths:
                            imgs, auds, vids, docs = await process_file(
                                file_paths,
                                get_agent_by_key(data.get("agent", "general")),
                            )
                            # Merge with existing media from data URLs
                            images = (images or []) + (imgs or [])
                            audios = (audios or []) + (auds or [])
                            videos = (videos or []) + (vids or [])
                            files = (files or []) + (docs or [])

                    # Extract media from query text
                    url_imgs, url_auds, url_vids, url_docs = extract_media_from_text(
                        query_text
                    )
                    if url_imgs:
                        images = (images or []) + url_imgs
                    if url_auds:
                        audios = (audios or []) + url_auds
                    if url_vids:
                        videos = (videos or []) + url_vids
                    if url_docs:
                        files = (files or []) + url_docs
                    await stream_agent(
                        query=query_text,
                        agent_key=data.get("agent", "general"),
                        images=images or None,
                        audios=audios or None,
                        videos=videos or None,
                        files=files or None,
                    )
                finally:
                    # Clean up temporary files
                    for temp_path in temp_files_to_clean:
                        try:
                            Path(temp_path).unlink()
                        except OSError:
                            pass
                continue

            await ctx.websocket.send_json(
                {"type": "error", "message": "Invalid data format."}
            )
    except WebSocketDisconnect:
        await cancel_current("cancelled (disconnect)")
        try:
            await asr_manager.close_session(ctx.asr_session_key)
        except Exception:
            pass
    except Exception:
        await ctx.websocket.close(code=1000, reason="Internal Server Error")
    finally:
        try:
            await asr_manager.close_session(ctx.asr_session_key)
        except Exception:
            pass


@router.get("/memory/list")
async def list_memory():
    return root_agent.db.get_user_memories(user_id=user_id) or []


@router.delete("/memory/delete")
async def delete_memory(memory_id: str):
    return root_agent.db.delete_user_memory(user_id=user_id, memory_id=memory_id)


@router.get("/memory/clear")
async def clear_memory():
    try:
        return root_agent.db.clear_memories(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Sessions management APIs
# ---------------------------


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """List all sessions for a user (defaults to current user)."""
    try:
        sessions = root_agent.db.get_sessions(SessionType.AGENT, user_id=user_id)

        if not isinstance(sessions, list):
            return {"sessions": []}

        # Sort sessions by updated_at (most recent first). Fall back to created_at if needed.
        sessions_sorted = sorted(
            sessions,
            key=lambda s: getattr(s, "updated_at", None)
            or getattr(s, "created_at", None)
            or 0,
            reverse=True,
        )

        result: List[Dict[str, Any]] = []
        for s in sessions_sorted:
            result.append(
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "session_name": s.session_data.get("session_name"),
                    "summary": s.summary,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                }
            )
        return {"sessions": result}
    except Exception as e: 
        logger.error(f"Failed to list sessions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str) -> Dict[str, Any]:
    """Retrieve chat history (messages) for a given session."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session_id")

        messages = root_agent.get_chat_history(session_id)
        formatted = [
            m.to_dict()
            for m in messages
            if m.to_dict().get("role") not in ("system", "tool")
        ]
        return {"session_id": session_id, "messages": formatted}
    
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to retrieve session history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a specific session by ID."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session_id")
        root_agent.delete_session(session_id)
        return {"deleted": True, "session_id": session_id}
    except Exception as e:  # pragma: no cover
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions")
async def clear_all_sessions(user: Optional[str] = None):
    """Clear all sessions for the user (or all if user not provided)."""
    try:
        ids = [s.session_id for s in root_agent.db.get_sessions(SessionType.AGENT, user_id=user)]
        root_agent.db.delete_sessions(ids)
        return {"cleared": True, "deleted_session_ids": ids}
    except Exception as e: 
        logger.error(f"Failed to clear sessions for user {user}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Title generation helper
# ---------------------------


async def generate_session_title(
    session_id: str,
    first_query: str,
    response: str,
) -> None:
    """Generate a concise session title using both user's first query and agent's first response."""
    logger.info(f"Generating title for session {session_id}...")
    try:
        prompt = f"""Your task is to generate a short and descriptive chat title in 3-6 words for user's query. It should indicate the main topic or intent of the conversation. Return title only, no quotes or trailing punctuation.

        User: {first_query}
        Assistant: {response}
        
        Title:"""

        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemma-3-4b-it", contents=prompt
        )

        title = (response.text or "No Title").strip().strip('"').strip()
        if title:
            root_agent.set_session_name(session_id, session_name=title)
    except Exception as e:
        logger.error(f"Failed to generate title for session {session_id}: {e}")
        # Don't propagate title generation errors - they're not critical


@router.get("/agents")
async def list_agents():
    return {"agents": list(AGENTS.keys())}
