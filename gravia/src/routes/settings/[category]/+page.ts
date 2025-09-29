import { settingsCategoryUrl } from '$lib/constants/api';
import type { PageLoad } from './$types';

export const load = (async ({ fetch, params }) => {
    const res = await fetch(settingsCategoryUrl(params.category));
    const settings = await res.json();
    return settings;
}) satisfies PageLoad;