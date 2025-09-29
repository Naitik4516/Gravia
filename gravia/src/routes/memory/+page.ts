import { CHAT_MEMORY_LIST_URL } from '$lib/constants/api';
import type { PageLoad } from './$types';

export const load = (async ({fetch}) => {
    const res = await fetch(CHAT_MEMORY_LIST_URL);
    const memories = await res.json();
    if (memories || memories.length) {
        return {memories};
    }
    else {
        return {memories: []};
    }
}) satisfies PageLoad;