import { EVENTS_STREAM_URL } from './constants/api';
import { emit } from '@tauri-apps/api/event';

// Simple event emitter pattern
export type SSEEventMap = {
  event: any;
  notification: NotificationPayload;
  error: string;
};

export type NotificationPayload = {
  id?: string;
  type?: 'alarm' | 'timer' | 'default' | 'reminder' | 'info' | string;
  title?: string;
  message?: string | { id?: number; name?: string; message?: string; [k: string]: any };
  at?: string | number;
  [k: string]: any;
};


class SSEService {
  private eventSourceEvents?: EventSource;
  private eventSourceNotifications?: EventSource;
  private reconnectDelay = 3000;
  private closed = false;

  start() {
    this.closed = false;
    this.openEventsStream();
    console.log('SSEService started');  
  }

  stop() {
    this.closed = true;
    this.eventSourceEvents?.close();
    this.eventSourceNotifications?.close();
    console.log('SSEService stopped');
  }

  private openEventsStream() {
    try {
      this.eventSourceEvents?.close();
      const es = new EventSource(EVENTS_STREAM_URL);
      this.eventSourceEvents = es;
      // Listen for specific event types
      es.addEventListener('status', (ev) => {
        if (!ev.data) return;
        
        // Try to parse as JSON first, but handle plain text gracefully
        let eventData;
        try {
          eventData = JSON.parse(ev.data);
        } catch {
          // Not JSON, treat as plain text
          eventData = ev.data;
        }
        
        emit('event', { type: 'status', data: eventData });
      });
      es.onerror = () => {
        emit('error', 'events stream error');
        es.close();
        if (!this.closed) setTimeout(() => this.openEventsStream(), this.reconnectDelay);
      };
    } catch (e) {
      console.error('Failed to start events stream', e);
    }
  }
}

export const sseService = new SSEService();
