import type { PageLoad } from './$types';
import { KNOWLEDGE_CONTENT_URL } from '$lib/constants/api';

export const load: PageLoad = async ({ fetch, url }) => {
  try {
    const limit = parseInt(url.searchParams.get('limit') || '20');
    const page = parseInt(url.searchParams.get('page') || '1');
    const sort_by = url.searchParams.get('sort_by') || undefined;
    const sort_order = url.searchParams.get('sort_order') as 'asc' | 'desc' | undefined;

    const searchParams = new URLSearchParams();

    if (limit) searchParams.append('limit', limit.toString());
    if (page) searchParams.append('page', page.toString());
    if (sort_by) searchParams.append('sort_by', sort_by);
    if (sort_order) searchParams.append('sort_order', sort_order);

    const response = await fetch(`${KNOWLEDGE_CONTENT_URL}?${searchParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Failed to fetch knowledge list:', response.statusText);
      return {
        items: [],
        total: 0,
        page: 1,
        limit: 20,
        has_more: false,
        total_pages: 1
      };
    }

    const res = await response.json();

    return {
      items: res.data || [],
      total: res.meta?.total_count || 0,
      page: res.meta?.page || 1,
      limit: res.meta?.limit || 20,
      has_more: (res.meta?.page || 1) < (res.meta?.total_pages || 1),
      total_pages: res.meta?.total_pages || 1
    }
  }
  catch (error) {
    console.error('Error loading knowledge list:', error);
    return {
      items: [],
      total: 0,
      page: 1,
      limit: 20,
      has_more: false,
      total_pages: 1
    };
  }
};
