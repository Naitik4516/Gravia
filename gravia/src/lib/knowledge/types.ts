export interface KnowledgeItem {
  id: string;
  name: string;
  description: string;
  file_type: string; // e.g. "url", "PDF", "Markdown"
  status: string; // e.g. "completed", "processing"
  status_message: string;
  created_at: number; // Unix timestamp
  updated_at: number; // Unix timestamp
  size?: number | null; // Size in bytes
  url?: string | null;
  path?: string | null;
  metadata: {
    tag?: string;
    user_tag?: string;
    [key: string]: any;
  };
  // Additional optional fields from API
  auth?: any;
  content_hash?: string | null;
  external_id?: string | null;
  file_data?: any;
  from_dict?: Record<string, any>;
  reader?: any;
  remote_content?: any;
  topics?: any;
}

// Legacy interface for backward compatibility
export interface LegacyKnowledgeItem {
  id: string;
  name: string;
  fileType: string; // e.g. Markdown, PDF, Docx
  description: string;
  updatedAt: string; // ISO date string
  tag?: string; // category label e.g. Guide, Spec
  sizeBytes: number;
}

export interface KnowledgeTableState {
  page: number;
  pageSize: number;
  sortBy: keyof KnowledgeItem | null;
  sortDir: 'asc' | 'desc';
  search: string;
  selected: Set<string>;
}
