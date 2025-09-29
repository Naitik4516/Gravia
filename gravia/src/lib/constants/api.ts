const PORT = import.meta.env.VITE_API_PORT || "5089";
const BASE = import.meta.env.VITE_API_BASE_URL || `http://localhost:${PORT}`;

// User
const USER_BASE = `${BASE}/user`;
const SIGNUP_URL = `${USER_BASE}/signup`;
const USER_PROFILE_URL = `${USER_BASE}/profile`;
// Chat
const CHAT_BASE = `${BASE}/chat`;

// Memory
const CHAT_MEMORY_LIST_URL = `${CHAT_BASE}/memory/list`;
const CHAT_MEMORY_DELETE_URL = `${CHAT_BASE}/memory/delete`;
const CHAT_MEMORY_CLEAR_URL = `${CHAT_BASE}/memory/clear`;

// Sessions
const CHAT_SESSIONS_URL = `${CHAT_BASE}/sessions`; // GET list, DELETE clear all sessions
const chatSessionHistoryUrl = (sessionId: string) => `${CHAT_BASE}/sessions/${sessionId}/history`;
const chatSessionUrl = (sessionId: string) => `${CHAT_BASE}/sessions/${sessionId}`; // DELETE single session

// Agents
const CHAT_AGENTS_URL = `${CHAT_BASE}/agents`;

// Settings
const settingsCategoryUrl = (categoryName: string) => `${BASE}/settings/category/${categoryName}`;
const SETTINGS_UPDATE_URL = `${BASE}/settings/update`;
const SETTINGS_UPDATE_CATEGORY_URL = `${BASE}/settings/update-category`;
const SETTINGS_UPDATE_PREFERENCES_URL = `${BASE}/settings/update-preferences`;
const SETTINGS_VOICES_URL = `${BASE}/settings/voices`;

// Server-Sent Events (SSE)
// Event stream for general backend status / progress events
const EVENTS_STREAM_URL = `${BASE}/events`;
// Notification stream (alarms, timers, default notifications)
const NOTIFICATIONS_STREAM_URL = `${BASE}/notifications`;

// Integrations
const INTEGRATIONS_URL = `${BASE}/integrations`;
const integrationConnectUrl = (toolkitKey: string) => `${BASE}/integrations/connect/${toolkitKey}`;
const integrationDisconnectUrl = (toolkitKey: string) => `${BASE}/integrations/disconnect/${toolkitKey}`;

// Knowledge
const KNOWLEDGE_BASE = `${BASE}/knowledge`;
const KNOWLEDGE_SOURCES_URL = `${KNOWLEDGE_BASE}/sources`;
const knowledgeDeleteSourceUrl = (sourceId: string) => `${KNOWLEDGE_BASE}/sources/${sourceId}`;
const KNOWLEDGE_SAVE_URL = `${KNOWLEDGE_BASE}/save`;

// Knowledge Content
const KNOWLEDGE_CONTENT_URL = `${KNOWLEDGE_BASE}/content`;
const knowledgeContentByIdUrl = (contentId: string) => `${KNOWLEDGE_BASE}/content/${contentId}`;
const KNOWLEDGE_SEARCH_URL = `${KNOWLEDGE_BASE}/search`;

export {
    PORT,
    BASE,
    SIGNUP_URL,
    USER_PROFILE_URL,
    CHAT_MEMORY_LIST_URL,
    CHAT_MEMORY_DELETE_URL,
    CHAT_MEMORY_CLEAR_URL,
    CHAT_SESSIONS_URL,
    chatSessionHistoryUrl,
    chatSessionUrl,
    CHAT_AGENTS_URL,
    settingsCategoryUrl,
    SETTINGS_UPDATE_URL,
    SETTINGS_UPDATE_CATEGORY_URL,
    SETTINGS_UPDATE_PREFERENCES_URL,
    SETTINGS_VOICES_URL,
    EVENTS_STREAM_URL,
    NOTIFICATIONS_STREAM_URL,
    INTEGRATIONS_URL,
    integrationConnectUrl,
    integrationDisconnectUrl,
    KNOWLEDGE_SOURCES_URL,
    knowledgeDeleteSourceUrl,
    KNOWLEDGE_SAVE_URL,
    KNOWLEDGE_CONTENT_URL,
    knowledgeContentByIdUrl,
    KNOWLEDGE_SEARCH_URL
};