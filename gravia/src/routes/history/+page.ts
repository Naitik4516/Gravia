import { CHAT_SESSIONS_URL } from '$lib/constants/api';
import type { PageLoad } from './$types';

export const load = (async ({fetch}) => {
    const res = await fetch(CHAT_SESSIONS_URL);
    const sessions = await res.json();

    return sessions;
}) satisfies PageLoad;