import { chatSessionHistoryUrl } from '$lib/constants/api';
import type { PageLoad } from './$types';

export const load = (async ({fetch, url}) => {
    const sessionId = url.searchParams.get('sessionId') || sessionStorage.getItem('sessionId') || undefined;
    if (!sessionId) {
        return {};
    }
    const res = await fetch(chatSessionHistoryUrl(sessionId));
    if (!res.ok) {
        console.error('Failed to load session history');
        return {};
    }
    const session = await res.json();

    return session
}) satisfies PageLoad;