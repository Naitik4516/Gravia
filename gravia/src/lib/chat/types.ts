// src/lib/types.ts
export type FileAttachment = {
  id: string; // Unique ID for keying in loops
  name: string;
  type: string; // MIME type
  size: number;
  dataUrl?: string; // For image previews
  fileObject?: File; // Keep the original file object for sending
  filePath?: string; // File path for Tauri mode
};

export type MessageRole = 'user' | 'assistant' | 'error';

export type MediaFile = {
  name: string;
  type: string;
  size?: number;
  filepath?: string;
  filePath?: string;
  dataUrl?: string;
};

export type Message = {
  id?: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  files?: FileAttachment[];
  audios?: MediaFile[];
  images?: MediaFile[];
  videos?: MediaFile[];
};

export type AgentType = 'general' | 'reasoning' | 'image';

