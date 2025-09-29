import type { PageLoad } from './$types';
import { USER_PROFILE_URL } from '$lib/constants/api';

export const load = (async ({fetch}) => {
    const res = await fetch(USER_PROFILE_URL);
    if (res.ok) {
        const profile = await res.json();
        return { profile };
    }
    
}) satisfies PageLoad;