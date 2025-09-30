import type { Message, FileAttachment } from './types';
import { fetch } from '@tauri-apps/plugin-http';
import { invoke } from '@tauri-apps/api/core';
import {PORT, BASE, USER_PROFILE_URL} from '$lib/constants/api';
import { goto } from '$app/navigation';


const SESSION_KEY = 'sessionId';

function getSessionId(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

function setSessionId(id: string) {
  try { sessionStorage.setItem(SESSION_KEY, id); } catch { /* ignore */ }
}

function clearSessionId() {
  try { sessionStorage.removeItem(SESSION_KEY); } catch { /* ignore */ }
}

export function createUserMessage(
  content: string,
  files?: FileAttachment[]
): Message {
  return {
    id: crypto.randomUUID(),
    role: 'user' as const,
    content,
    timestamp: new Date(),
    files
  };
}

export function createErrorMessage(content: string): Message {
  return {
    id: crypto.randomUUID(),
    role: 'error',
    content,
    timestamp: new Date()
  };
}

export function getMessagePosition(messages: Message[], index: number): "single" | "first" | "middle" | "last" {
  const currentMessage = messages[index];

  if (currentMessage.role === 'user' || currentMessage.role === 'error') {
    return 'single';
  }

  if (messages.length <= 1 || index < 0 || index >= messages.length) {
    return "single";
  }

  const prev = index > 0 ? messages[index - 1] : null;
  const next = index < messages.length - 1 ? messages[index + 1] : null;

  const isPrevSameRoleAI = prev && prev.role === 'assistant' && currentMessage.role === 'assistant';
  const isNextSameRoleAI = next && next.role === 'assistant' && currentMessage.role === 'assistant';

  if (isPrevSameRoleAI && isNextSameRoleAI) return "middle";
  if (isPrevSameRoleAI) return "last";
  if (isNextSameRoleAI) return "first";
  return "single";
}

export type ChatServerMessage =
  | { type: 'message_chunk'; message: string; }
  | { type: 'event'; message: string }
  | { type: 'error'; message: string }
  | { type: 'session_created'; session_id: string }
  | { type: 'message_end' }
  | { type: 'tts_start'; message?: string }
  | { type: 'tts_complete'; message?: string }
  | { type: 'transcription_partial'; message: string }
  | { type: 'transcription_final'; message: string }
  | { type: 'file_artifact'; file: { name: string; path: string; data_b64?: string; } }
  | { type: 'image'; data: string; mime?: string; name?: string };

type EventName = 'open' | 'close' | 'error' | 'start' | 'chunk' | 'end' | 'event' |  'session_created' | 'tts_start' | 'tts_complete' | 'new_chat' | 'transcription_partial' | 'transcription_final' | 'listening_start' | 'listening_stop' | 'file_artifact' | 'image';
type EventHandler = (data?: any) => void;

interface PendingSend {
  query: string;
  files?: FileAttachment[];
  agent: string;
}

class ChatClient {
  private ws: WebSocket | null = null;
  private url: string;
  private baseWsUrl: string;
  private connected = false;
  private connecting = false;
  private listeners: Record<EventName, Set<EventHandler>> = {
    open: new Set(),
    close: new Set(),
    error: new Set(),
    start: new Set(),
    chunk: new Set(),
    end: new Set(),
    event: new Set(),
    session_created: new Set(),
    tts_start: new Set(),
    tts_complete: new Set(),
    new_chat: new Set(),
    transcription_partial: new Set(),
    transcription_final: new Set(),
    listening_start: new Set(),
    listening_stop: new Set(),
    file_artifact: new Set(),
    image: new Set(),
  };
  private reconnectAttempts = 0;
  private maxReconnectDelay = 8000;
  private pendingQueue: PendingSend[] = [];
  private endDebounceTimer: any = null;
  private inactivityTimeout = 3000;

  constructor(baseWsUrl = `ws://localhost:${PORT}/chat/ws`) {
    this.baseWsUrl = baseWsUrl;
    const sessionId = getSessionId();
    this.url = sessionId ? `${baseWsUrl}?session_id=${encodeURIComponent(sessionId)}` : baseWsUrl;
  }

  on(event: EventName, handler: EventHandler) {
    this.listeners[event].add(handler);
    return () => this.listeners[event].delete(handler);
  }

  private emit(event: EventName, data?: any) {
    this.listeners[event].forEach((cb) => {
      try { cb(data); } catch { }
    });
  }

  private scheduleEndEmit() {
    if (this.endDebounceTimer) clearTimeout(this.endDebounceTimer);
    this.endDebounceTimer = setTimeout(() => this.emit('end'), this.inactivityTimeout);
  }

  async connect() {
    if (this.connected || this.connecting) return;
    this.connecting = true;
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.connected = true;
        this.connecting = false;
        this.reconnectAttempts = 0;
        this.emit('open');
        if (this.pendingQueue.length) {
          const queue = [...this.pendingQueue];
          this.pendingQueue = [];
          queue.forEach((p) => this.sendMessage(p.query, p.files, p.agent));
        }
      };

      this.ws.onclose = (event: CloseEvent) => {
        const wasConnected = this.connected;
        this.connected = false;
        this.connecting = false;
        this.emit('close');
        if (wasConnected) {
          this.scheduleEndEmit();
        }

        // Emit error for unexpected disconnections
        if (!event.wasClean) {
          console.error(`WebSocket connection closed unexpectedly. Code: ${event.code}, Reason: ${event.reason || 'Unknown'}`);
        }

        // If this was an initial connection failure (wasConnected === false),
        // probe the HTTP endpoint to detect a 403 and redirect if necessary.
        if (!wasConnected) {
          // fire-and-forget
          this.checkAuthAndRedirect();
        }

        this.tryReconnect();
      };

      // this.ws.onerror = (err: Event) => {
        // this.emit('error', {
        //   message: 'Unexpected error occurred. \n Error details: ' + (err instanceof ErrorEvent ? err.message : 'Unknown error')
        // });
      // };

      this.ws.onmessage = (ev: any) => {
        this.handleMessage(ev.data);
      };
    } catch (e) {
      this.connecting = false;
      console.error('WebSocket connection failed:', e);
      // On exceptions while trying to connect, check for HTTP 403 and redirect if found
      this.checkAuthAndRedirect();
    }
  }

  private handleMessage(data: string) {
    let messageData: ChatServerMessage | null = null;
    try {
      messageData = JSON.parse(data);
    } catch {
      return;
    }

    if (!messageData || typeof messageData !== 'object' || !('type' in messageData)) return;

    switch (messageData.type) {
      case 'message_chunk':
        if (this.endDebounceTimer) clearTimeout(this.endDebounceTimer);
        this.emit('chunk', messageData);
        this.scheduleEndEmit();
        break;
      case 'event':
        this.emit('event', messageData.message);
        break;
      case 'error':
        this.emit('error', messageData.message);
        if (messageData.message.includes('403')) {
          goto('/auth/signup');
        }
        this.scheduleEndEmit();
        break;
      case 'session_created':
        if (messageData.session_id) {
          setSessionId(messageData.session_id);
          this.emit('session_created', messageData.session_id);
          this.url = `${this.baseWsUrl}?session_id=${encodeURIComponent(messageData.session_id)}`;
        }
        break;
      case 'message_end':
        if (this.endDebounceTimer) {
          clearTimeout(this.endDebounceTimer);
          this.endDebounceTimer = null;
        }
        this.emit('end');
        break;
      case 'tts_start':
        this.emit('tts_start', messageData.message);
        break;
      case 'tts_complete':
        this.emit('tts_complete', messageData.message);
        break;
      case 'transcription_partial':
        this.emit('transcription_partial', messageData.message);
        break;
      case 'transcription_final':
        this.emit('transcription_final', messageData.message);
        break;
      case 'file_artifact':
        this.emit('file_artifact', messageData.file);
        break;
      case 'image':
        this.emit('image', messageData);
        break;
    }
  }

  private tryReconnect() {
    if (this.reconnectAttempts >= 5) {
      this.emit('error', {
        message: 'Failed to reconnect after multiple attempts. Please check your connection and try again.'
      });
      return;
    }

    const delay = Math.min((2 ** this.reconnectAttempts) * 500, this.maxReconnectDelay);
    this.reconnectAttempts += 1;

    setTimeout(() => {
      if (!this.connected && !this.connecting) {
        this.connect();
      }
    }, delay);
  }

  async newChat() {
    clearSessionId();
    this.url = this.baseWsUrl;
    if (this.ws) {
      try {
        this.ws.close();
      } catch { }
      this.ws = null;
    }
    this.connected = false;
    this.connecting = false;
    this.reconnectAttempts = 0;
    // Emit new_chat event to notify UI components
    this.emit('new_chat');
    await this.connect();
  }

  async sendMessage(query: string, files?: FileAttachment[], agent: string = 'general') {
    // Optional: run classifier before sending (could be moved outside if UI controls flow)
    // This expects last messages managed externally; left as pass-through here.
    console.log('Sending message', { query, files, agent });

    if (!query.trim() && (!files || !files.length)) return;
    const isConnected = this.ws && this.ws.readyState === WebSocket.OPEN;
    if (!this.connected || !this.ws || !isConnected) {
      this.pendingQueue.push({ query, files, agent });
      await this.connect();
      return;
    }

    this.emit('start');
    const payload: any = { query, agent };

    if (files && files.length) {
      payload.files = await Promise.all(
        files.map(async (f) => {
          if (f.fileObject) {
            const arrayBuf = await f.fileObject.arrayBuffer();
            const b64 = this.arrayBufferToBase64(arrayBuf);
            return {
              name: f.name,
              type: f.type,
              size: f.size,
              data_b64: b64,
            };
          }
          if (f.filePath) {
            return {
              name: f.name,
              type: f.type,
              size: f.size,
              path: f.filePath,
            };
          }
          if (f.dataUrl?.startsWith("data:")) {
            const base64Part = f.dataUrl.split(",")[1];
            return {
              name: f.name,
              type: f.type,
              size: f.size,
              data_b64: base64Part,
            };
          }
          return { name: f.name, type: f.type, size: f.size };
        }),
      );
    }

    try {
      const message = JSON.stringify(payload);
      this.ws.send(message);
    } catch (e) {
      this.emit('error', {
        message: `Failed to send message: ${e instanceof Error ? e.message : 'Unknown error'}`
      });
    }
  }

  interrupt() {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'interrupt' }));
    }
    if (this.endDebounceTimer) {
      clearTimeout(this.endDebounceTimer);
      this.endDebounceTimer = null;
    }
    this.emit('end');
  }

  startVoiceCapture() {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'start_voice' }));
    }
  }

  speak(text: string) {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'speak', text }));
    }
  }

  stopSpeaking() {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'stop_speaking' }));
    }
  }

  startListening() {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'start_listening' }));
      this.emit('listening_start');
    }
  }

  stopListening() {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type: 'stop_listening' }));
      this.emit('listening_stop');
    }
  }

  toggleListening() {
    // This is a client-side concept, so we'll just toggle the listening state
    // The actual start/stop is handled by the shortcut presses
    // We can emit an event to let the UI know, but the core logic is in hooks.client.ts
    console.log("Toggling listening state via chatClient");
  }

  private arrayBufferToBase64(buf: ArrayBuffer) {
    let binary = '';
    const bytes = new Uint8Array(buf);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  // New helper: probe user profile endpoint and redirect on auth failures
  private async checkAuthAndRedirect() {
    try {
      const res = await fetch(USER_PROFILE_URL, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
        },
      });
      // plugin-http response exposes status; guard defensively
      const status = (res && (res as any).status) ? (res as any).status : undefined;
      if (status === 401 || status === 404 || status === 403) {
        console.warn(`Received ${status} from profile endpoint; redirecting to signup.`);
        goto('/auth/signup');
      }
    } catch {
      // ignore network errors — reconnection logic will continue
    }
  }
}

export const chatClient = new ChatClient();

// Classifier integration helper
export interface ClassifierFrontendMessage {
  role: string; // 'user' | 'assistant'
  content: string;
  timestamp?: string; // ISO string
  triggered_screenshot?: boolean;
}

export interface ClassifyResult {
  classification: {
    needs_screenshot: boolean;
    confidence: number;
    screenshot_score: number;
    no_screenshot_score: number;
    reasoning: string[];
    context_info: {
      has_context: boolean;
      context_type?: string | null;
      recent_screenshot: boolean;
      assistant_gave_instructions: boolean;
      user_in_middle_of_task: boolean;
      context_strength: number;
    };
    screenshot_base64?: string | null;
  };
  screenshot_base64?: string | null;
}

export async function classifyQueryWithScreenshot(
  recentMessages: Message[],
  query: string,
  enabled: boolean = true
): Promise<ClassifyResult | null> {
  if (!enabled) return null;
  try {
    const payload: ClassifierFrontendMessage[] = recentMessages.slice(-5).map(m => {
      let ts: Date;
      if (!m.timestamp) {
        ts = new Date();
      } else if (typeof m.timestamp === 'string') {
        ts = new Date(m.timestamp);
      } else {
        ts = m.timestamp;
      }
      return {
        role: m.role === 'error' ? 'user' : m.role,
        content: m.content,
        timestamp: ts.toISOString(),
      };
    });
    // NOTE: backend expects snake_case `recent_messages` per Rust command signature
    // Send both snake_case and camelCase for backward/forward compatibility depending on backend expectation
    return await invoke<ClassifyResult>('classify_and_maybe_capture', {
      recent_messages: payload,
      recentMessages: payload,
      query
    });
  } catch (e) {
    console.warn('Classifier invocation failed; rethrowing to allow caller fallback.', e);
    throw e;
  }
}

export async function clearAllSessions() {
  const res = await fetch(`${BASE}/chat/sessions`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to clear sessions');
}

export async function deleteSession(sessionId: string) {
  console.log('Deleting session', sessionId);
  const res = await fetch(`${BASE}/chat/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete session');
}

export async function getSessionHistory(sessionId: string) {
  const res = await fetch(`${BASE}/chat/sessions/${encodeURIComponent(sessionId)}/history`);
  if (!res.ok) throw new Error('Failed to fetch session history');
  return res.json();
}

export async function listMemory() {
  const res = await fetch(`${BASE}/chat/memory/list`);
  if (!res.ok) throw new Error('Failed to list memory');
  return res.json();
}

export async function deleteMemory(memoryId: string) {
  const res = await fetch(`${BASE}/chat/memory/delete`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ memory_id: memoryId }),
  });
  if (!res.ok) throw new Error('Failed to delete memory');
}

export async function clearMemory() {
  const res = await fetch(`${BASE}/chat/memory/clear`);
  if (!res.ok) throw new Error('Failed to clear memory');
}
