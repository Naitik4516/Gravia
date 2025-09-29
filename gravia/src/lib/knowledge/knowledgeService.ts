import { 
  KNOWLEDGE_CONTENT_URL, 
  knowledgeContentByIdUrl, 
  KNOWLEDGE_SEARCH_URL 
} from '$lib/constants/api';
import type { KnowledgeItem } from './types';

export interface KnowledgeListResponse {
  items: KnowledgeItem[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
  total_pages: number;
}

export interface KnowledgeApiResponse {
  data: KnowledgeItem[];
  meta: {
    page: number;
    limit: number;
    total_pages: number;
    total_count: number;
  };
}

export interface KnowledgeSearchResponse {
  results: KnowledgeItem[];
  total: number;
  query: string;
}

export interface CreateKnowledgeRequest {
  name: string;
  description?: string;
  tag?: string;
  source_type: 'file' | 'url' | 'text';
  chunking_method?: 'document' | 'semantic';
  path?: string;
  url?: string;
  text?: string;
}

export interface UpdateKnowledgeRequest {
  name?: string;
  description?: string;
  tag?: string;
}

export class KnowledgeService {
  /**
   * Fetch knowledge content list with pagination and sorting
   */
  static async getKnowledgeList(params: {
    limit?: number;
    page?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
  } = {}): Promise<KnowledgeListResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.limit) searchParams.append('limit', params.limit.toString());
    if (params.page) searchParams.append('page', params.page.toString());
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.sort_order) searchParams.append('sort_order', params.sort_order);

    const url = `${KNOWLEDGE_CONTENT_URL}?${searchParams.toString()}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch knowledge list: ${response.statusText}`);
    }

    const apiResponse: KnowledgeApiResponse = await response.json();
    
    // Transform the API response to match our expected structure
    return {
      items: apiResponse.data || [],
      total: apiResponse.meta?.total_count || 0,
      page: apiResponse.meta?.page || 1,
      limit: apiResponse.meta?.limit || 20,
      has_more: (apiResponse.meta?.page || 1) < (apiResponse.meta?.total_pages || 1),
      total_pages: apiResponse.meta?.total_pages || 1
    };
  }

  /**
   * Create new knowledge content
   */
  static async createKnowledge(data: CreateKnowledgeRequest): Promise<KnowledgeItem> {
    const formData = new FormData();
    
    formData.append('name', data.name);
    if (data.description) formData.append('description', data.description);
    if (data.tag) formData.append('tag', data.tag);
    formData.append('source_type', data.source_type);
    if (data.chunking_method) formData.append('chunking_method', data.chunking_method);
    
    if (data.source_type === 'file' && data.path) {
      formData.append('path', data.path);
    } else if (data.source_type === 'url' && data.url) {
      formData.append('url', data.url);
    } else if (data.source_type === 'text' && data.text) {
      formData.append('text', data.text);
    }

    const response = await fetch(KNOWLEDGE_CONTENT_URL, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to create knowledge: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get knowledge content by ID
   */
  static async getKnowledgeById(contentId: string): Promise<KnowledgeItem> {
    const response = await fetch(knowledgeContentByIdUrl(contentId), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch knowledge: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Update knowledge content
   */
  static async updateKnowledge(contentId: string, data: UpdateKnowledgeRequest): Promise<KnowledgeItem> {
    const formData = new URLSearchParams();
    
    if (data.name) formData.append('name', data.name);
    if (data.description) formData.append('description', data.description);
    if (data.tag) formData.append('tag', data.tag);

    const response = await fetch(knowledgeContentByIdUrl(contentId), {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to update knowledge: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Delete knowledge content by ID
   */
  static async deleteKnowledge(contentId: string): Promise<void> {
    const response = await fetch(knowledgeContentByIdUrl(contentId), {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete knowledge: ${response.statusText}`);
    }
  }

  /**
   * Delete all knowledge content
   */
  static async deleteAllKnowledge(): Promise<void> {
    const response = await fetch(KNOWLEDGE_CONTENT_URL, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete all knowledge: ${response.statusText}`);
    }
  }

  /**
   * Delete multiple knowledge items by IDs
   */
  static async deleteMultipleKnowledge(contentIds: string[]): Promise<void> {
    // Since the API doesn't have a bulk delete endpoint, we'll delete them one by one
    const deletePromises = contentIds.map(id => this.deleteKnowledge(id));
    await Promise.all(deletePromises);
  }

  /**
   * Search knowledge content
   */
  static async searchKnowledge(query: string, limit: number = 10, filter?: any): Promise<KnowledgeSearchResponse> {
    const searchParams = new URLSearchParams();
    searchParams.append('query', query);
    searchParams.append('limit', limit.toString());

    const url = `${KNOWLEDGE_SEARCH_URL}?${searchParams.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      body: filter ? JSON.stringify(filter) : undefined,
    });

    if (!response.ok) {
      throw new Error(`Failed to search knowledge: ${response.statusText}`);
    }

    return response.json();
  }
}