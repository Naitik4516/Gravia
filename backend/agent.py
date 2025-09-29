import asyncio
from typing import Any, Callable, Dict, Literal
from urllib.parse import urlparse

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini

from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.sleep import SleepTools
from agno.tools.webbrowser import WebBrowserTools
from agno.tools.website import WebsiteTools
from google.genai import types

from event_handler import send_event
from knowledge_manager import knowledge
from prompts import get_root_instructions, get_root_prompt, reasoning_agent_introduction

from tools.additional import (
    WeatherToolkit,
    take_screenshot,
    open_app,
    close_app,
    get_active_explorer_path,
    get_active_explorer_selected_paths,
)
from tools.alarms import AlarmTools
from tools.code_interpreter import SafeCodeExecutor
from tools.composio_toolkits import toolkits as composio_toolkits
from tools.desktop import DesktopTools
from tools.file_converter import FileConverterToolkit
# from tools.music_player import MusicPlayerToolkit
from utils.data_handler import settings, user
from utils.logging_config import logger
from config import GEMINI_API_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY


def _get_profile():
    # Read profile on-demand to avoid stale copies
    try:
        return user.profile
    except Exception:
        return None

preferences = settings.get("preferences", {})
model = settings.get("primary_model")
reasoning_model = settings.get("reasoning_model")
image_model = settings.get("image_model", "gemini-2.0-flash-preview-image-generation")
enable_memory = bool(settings.get("memory", True))
num_history_sessions = int(settings.get("num_history_sessions", 3))
generate_session_summaries = bool(settings.get("generate_session_summaries", False))
add_session_summary_to_context = bool(
    settings.get("add_session_summary_to_context", True)
)
add_history_to_context = bool(settings.get("add_history_to_context", True))
add_datetime_to_context = bool(settings.get("add_datetime_to_context", True))
search_knowledge_enabled = bool(settings.get("search_knowledge", True))
# image_model = "gemini-2.0-flash-preview-image-generation"
telementry_enabled = settings.get("telemetry", True)

db = SqliteDb(db_file="data/agent.db")


if telementry_enabled:
    from openinference.instrumentation.agno import AgnoInstrumentor
    from opentelemetry import trace as trace_api
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    import base64
    import os

    # Set environment variables for Langfuse
    LANGFUSE_AUTH = base64.b64encode(
        f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
    ).decode()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = (
        "https://us.cloud.langfuse.com/api/public/otel"
    )
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

    # Configure the tracer provider
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
    trace_api.set_tracer_provider(tracer_provider=tracer_provider)

    # Start instrumenting agno
    AgnoInstrumentor().instrument()


def _map_safety(level: str):
    lvl = (level or "high").lower()
    if lvl == "off":
        return types.HarmBlockThreshold.BLOCK_NONE
    if lvl == "low":
        return types.HarmBlockThreshold.BLOCK_ONLY_HIGH
    if lvl == "medium":
        return types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    return types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE


safety_level = settings.get("safety_filters", "medium")
safety_settings = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=_map_safety(safety_level),
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=_map_safety(safety_level),
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=_map_safety(safety_level),
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
        if safety_level == "off"
        else _map_safety(safety_level),
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
        threshold=types.HarmBlockThreshold.BLOCK_NONE
        if safety_level == "off"
        else _map_safety(safety_level),
    ),
]


class GeminiWithErrorHandling(Gemini):
    """Gemini model wrapper with enhanced error handling for API issues"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = 3
        self.base_delay = 1.0
        self.api_key = GEMINI_API_KEY

    async def _handle_api_error(self, error: Exception, attempt: int = 1) -> None:
        """Handle specific Gemini API errors with appropriate user feedback"""
        error_str = str(error)
        logger.error(f"Gemini API error (attempt {attempt}): {error_str}")

        # Parse rate limit errors
        if "429" in error_str or "Too Many Requests" in error_str:
            if "retry in" in error_str.lower():
                # Extract retry delay from error message
                import re

                match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_str.lower())
                if match:
                    delay = float(match.group(1))
                    logger.info(f"Rate limited. Retrying in {delay} seconds...")
                    await send_event(
                        f"Rate limited. Waiting {int(delay)} seconds before retrying..."
                    )
                    await asyncio.sleep(delay)
                    return

            # Default exponential backoff for rate limits
            delay = self.base_delay * (2 ** (attempt - 1))
            logger.info(f"Rate limited. Retrying in {delay} seconds...")
            await send_event(f"API rate limited. Retrying in {int(delay)} seconds...")
            await asyncio.sleep(delay)
            return

        # Handle quota exceeded errors
        if (
            "quota exceeded" in error_str.lower()
            or "resource_exhausted" in error_str.lower()
        ):
            error_msg = "API quota exceeded. Please check your Gemini API billing and usage limits."
            logger.error(error_msg)
            await send_event(error_msg)
            raise Exception(error_msg)

        # Handle chunk too big errors
        if "chunk too big" in error_str.lower():
            error_msg = "Input is too large for the model. Please try with shorter text or fewer images."
            logger.error(error_msg)
            await send_event(error_msg)
            raise Exception(error_msg)

        # Handle other specific errors
        if "invalid_argument" in error_str.lower():
            error_msg = "Invalid request format. Please try rephrasing your query."
            logger.error(error_msg)
            await send_event(error_msg)
            raise Exception(error_msg)

        # For unknown errors, provide generic message
        error_msg = f"API error occurred: {error_str[:200]}..."
        logger.error(error_msg)
        await send_event("Temporary API issue. Please try again.")
        raise Exception(error_msg)

    async def _make_request_with_retry(self, request_func, *args, **kwargs):
        """Make API request with retry logic for recoverable errors"""
        for attempt in range(1, self.max_retries + 1):
            try:
                return await request_func(*args, **kwargs)
            except Exception as e:
                error_str = str(e)

                # Only retry on specific recoverable errors
                if (
                    "429" in error_str
                    or "Too Many Requests" in error_str
                    or "rate" in error_str.lower()
                    or "quota" in error_str.lower()
                ):
                    if attempt < self.max_retries:
                        await self._handle_api_error(e, attempt)
                        continue
                    else:
                        # Final attempt failed
                        await self._handle_api_error(e, attempt)
                        raise e
                else:
                    # Non-recoverable error, don't retry
                    await self._handle_api_error(e, attempt)
                    raise e


tools = [
    SafeCodeExecutor().execute_code,
    open_app,
    close_app,
    get_active_explorer_path,
    get_active_explorer_selected_paths,
    take_screenshot,
    AlarmTools(),
    DesktopTools(),
    # MusicPlayerToolkit(),
    FileConverterToolkit(),
    WeatherToolkit(),
    SleepTools(),
    WebsiteTools(),
    WebBrowserTools(),
    Newspaper4kTools(),
]


def _rebuild_tools():
    """Rebuild the tools list with current composio toolkits."""
    global tools
    tools = [
        SafeCodeExecutor().execute_code,
        open_app,
        close_app,
        get_active_explorer_path,
        get_active_explorer_selected_paths,
        take_screenshot,
        AlarmTools(),
        DesktopTools(),
        # MusicPlayerToolkit(),
        FileConverterToolkit(),
        WeatherToolkit(),
        SleepTools(),
        WebsiteTools(),
        WebBrowserTools(),
        Newspaper4kTools(),
    ]
    tools += composio_toolkits


# Initialize tools
_rebuild_tools()


async def event_sending_hook(
    function_name: str, function_call: Callable, arguments: Dict[str, Any]
):
    """A tool hook to send events before and after tool execution."""

    tool_name = function_name
    tool_args = arguments

    logger.info(f"Using tool: {tool_name}")
    logger.info(f"With arguments: {tool_args}")

    event_message = ""
    if tool_name == "execute_code":
        event_message = "Using code interpreter..."
    elif tool_name == "play_music":
        song_name = tool_args.get("song_name", "")
        event_message = f"Playing {song_name}" if song_name else "Playing music"
    elif tool_name == "pause_music":
        event_message = "Music paused."
    elif tool_name == "open_page":
        event_message = f"Opening {tool_args.get('url', 'webpage')}"
    elif tool_name == "open_app":
        event_message = f"Searching {tool_args.get('app_name', 'app')}..."
    elif tool_name == "close_app":
        event_message = f"Closing {tool_args.get('app_name', 'app')}..."
    elif tool_name == "get_active_explorer_path":
        event_message = "Getting active Explorer path..."
    elif tool_name == "get_active_explorer_selected_paths":
        event_message = "Getting selected files in active Explorer..."
    elif tool_name == "read_url":
        url = tool_args.get("url", "")
        if url:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "") if parsed_url.netloc else url
            event_message = f"Reading {domain}..."
        else:
            event_message = "Reading webpage..."
    elif tool_name == "read_article":
        event_message = "Reading article..."
    elif tool_name == "sleep":
        duration = tool_args.get("seconds", "")
        event_message = f"Sleeping for {duration} seconds"
    elif tool_name == "think":
        event_message = "Thinking..."
    elif tool_name in [
        "composio_search_amazon",
        "composio_search_duck_duck_go_search",
        "composio_search_event_search",
        "composio_search_exa_answer",
        "composio_search_exa_similarlink",
        "composio_search_finance_search",
        "composio_search_flights",
        "composio_search_google_maps_search",
        "composio_search_hotels",
        "composio_search_image_search",
        "composio_search_news_search",
        "composio_search_scholar_search",
        "composio_search_search",
        "composio_search_shopping_search",
        "composio_search_tavily_search",
        "composio_search_trends_search",
        "composio_search_trip_advisor",
        "composio_search_walmart",
    ]:
        event_message = "Browsing..."
    elif tool_name in ['gmail_create_email_draft', 'gmail_fetch_emails', 'gmail_get_contacts', 'gmail_get_people', 'gmail_move_to_trash', 'gmail_reply_to_thread', 'gmail_search_people', 'gmail_send_draft', 'gmail_send_email']:
        event_message = "Using Gmail..."
    elif tool_name in ['googlecalendar_create_event', 'googlecalendar_events_list', 'googlecalendar_find_event', 'googlecalendar_find_free_slots', 'googlecalendar_free_busy_query', 'googlecalendar_get_calendar', 'googlecalendar_list_calendars', 'googlecalendar_quick_add', 'googlecalendar_update_event']:
        event_message = "Using Google Calendar..."
    elif tool_name == "gemini_generate_image":
        event_message = "Generating image..."
    elif tool_name == "gemini_generate_videos":
        event_message = "Generating video..."
    elif tool_name == "gemini_wait_for_video":
        event_message = "Processing video..."

    if event_message:
        await send_event(event_message)

    try:
        result = function_call(**arguments)
        if asyncio.iscoroutine(result):
            result = await result
    except Exception as e:
        error_message = f"Failed to run tool {tool_name}: {e}"
        logger.error(error_message)
        await send_event(error_message)
        raise

    return result


def get_agent(agent_type: Literal["general", "reasoning"] = "general") -> Agent:
    model_id = model if agent_type == "general" else reasoning_model
    # Build agent using current profile at call time
    current_profile = _get_profile()
    # Ensure we always pass a Profile object to get_root_instructions
    if current_profile is None:
        from schemas import Profile as _ProfileClass

        current_profile = _ProfileClass()
    return Agent(
        model=GeminiWithErrorHandling(id=model_id, safety_settings=safety_settings),
        description=get_root_prompt()
        if agent_type == "general"
        else reasoning_agent_introduction,
        instructions=get_root_instructions(current_profile, preferences)
        if agent_type == "general"
        else None,
        markdown=True,
        reasoning=True if agent_type == "reasoning" else False,
        # reasoning_model=reasoning_model if agent_type == "reasoning" else None,
        db=db,
        enable_agentic_memory=enable_memory,
        add_session_summary_to_context=add_session_summary_to_context,
        add_history_to_context=add_history_to_context,
        add_datetime_to_context=add_datetime_to_context,
        search_session_history=True,
        enable_session_summaries=generate_session_summaries,
        num_history_sessions=num_history_sessions,
        tool_hooks=[event_sending_hook],
        tools=tools,
        knowledge=knowledge,
        search_knowledge=search_knowledge_enabled,
        telemetry=False,
        # debug_mode=True,
    )


root_agent = get_agent()

reasoning_agent = get_agent(agent_type="reasoning")


# Registry of available agents for dynamic selection
AGENTS = {"general": root_agent, "reasoning": reasoning_agent}


def get_agent_by_key(key: str):
    if key == "image":
        image_agent_model = GeminiWithErrorHandling(
            id=image_model, safety_settings=safety_settings
        )
        if image_model == "gemini-2.0-flash-preview-image-generation":
            image_agent_model.response_modalities = ["TEXT", "IMAGE"]

        image_agent = Agent(
            model=image_agent_model,
            # description="You are an AI agent that can generate and edit images.",
            # instructions="Try to understand the user's image requirements and generate or edit images accordingly.",
            db=db,
            tool_hooks=[event_sending_hook],
            telemetry=False,
        )

        return image_agent
    else:
        return AGENTS.get(key or "general", root_agent)


def refresh_agents(updated_data=None):
    """Rebuild agent instances when user data changes.

    This will recreate the root and reasoning agents so they pick up a fresh
    profile/instructions. It's registered as a callback from the user data
    handler.
    """
    global root_agent, reasoning_agent, AGENTS
    try:
        root_agent = get_agent()
        reasoning_agent = get_agent(agent_type="reasoning")
        AGENTS = {"general": root_agent, "reasoning": reasoning_agent}
    except Exception:
        # Best-effort refresh; avoid crashing caller
        logger.exception("Failed to refresh agents")


def refresh_settings(updated_data=None):
    """Refresh global settings variables when settings data changes.

    This updates all the global settings variables from the current settings
    data, rebuilds safety_settings, and refreshes agents and integrations.
    """
    global preferences, model, reasoning_model, image_model, enable_memory, num_history_sessions, generate_session_summaries, add_session_summary_to_context, add_history_to_context, add_datetime_to_context, search_knowledge_enabled, telementry_enabled, safety_level, safety_settings

    preferences = settings.get("preferences", {})
    model = settings.get("primary_model")
    reasoning_model = settings.get("reasoning_model")
    image_model = settings.get("image_model", "gemini-2.0-flash-preview-image-generation")
    enable_memory = bool(settings.get("memory", True))
    num_history_sessions = int(settings.get("num_history_sessions", 3))
    generate_session_summaries = bool(settings.get("generate_session_summaries", False))
    add_session_summary_to_context = bool(
        settings.get("add_session_summary_to_context", True)
    )
    add_history_to_context = bool(settings.get("add_history_to_context", True))
    add_datetime_to_context = bool(settings.get("add_datetime_to_context", True))
    search_knowledge_enabled = bool(settings.get("search_knowledge", True))
    telementry_enabled = settings.get("telemetry", True)
    safety_level = settings.get("safety_filters", "medium")

    # Rebuild safety_settings from the updated safety_level
    safety_settings[:] = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=_map_safety(safety_level),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=_map_safety(safety_level),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=_map_safety(safety_level),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
            if safety_level == "off"
            else _map_safety(safety_level),
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=types.HarmBlockThreshold.BLOCK_NONE
            if safety_level == "off"
            else _map_safety(safety_level),
        ),
    ]

    # Refresh agents to pick up the new settings
    refresh_agents()
    
    # Also refresh integrations (composio tools) since they may have changed
    refresh_integrations()


def refresh_integrations(updated_data=None):
    """Refresh composio toolkits when integrations data changes.

    This rebuilds the composio toolkits list based on enabled integrations,
    updates the tools list, and refreshes agents.
    """
    from tools.composio_toolkits import refresh_toolkits
    
    # Refresh the composio toolkits
    refresh_toolkits()
    
    # Rebuild the tools list with updated composio toolkits
    _rebuild_tools()
    
    # Refresh agents to pick up the new tools
    refresh_agents()


# Register a callback so agent instances are refreshed when user data changes
try:
    user.register_callback(refresh_agents)
except Exception:
    logger.debug("Could not register user data callback for agent refresh")

# Register a callback so settings and agents are refreshed when settings data changes
try:
    settings.register_callback(refresh_settings)
except Exception:
    logger.debug("Could not register settings data callback for refresh")
