import { USER_PROFILE_URL } from '$lib/constants/api';
import { globalState } from '$lib/state.svelte';

export async function fetchUserProfile(): Promise<any | null> {
  // Always run in browser context; caller should call from onMount or client-side code.
  try {
    const res = await fetch(USER_PROFILE_URL, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (res.status === 401 || res.status === 404) {
      // No user session -> redirect to signup/login flow
      // But avoid redirecting if we're already on an auth route (to prevent loops)
      if (typeof window !== 'undefined') {
        const pathname = window.location.pathname || '';
        if (!pathname.startsWith('/auth')) {
          // Use replace so we don't pollute history and to avoid repeated push
          window.location.replace('/auth/signup');
        } else {
          // already on auth page, don't redirect — let the auth UI handle state
          console.debug('fetchUserProfile: unauthenticated but already on auth route, skipping redirect');
        }
      }
      return null;
    }

    if (!res.ok) {
      // Other non-ok statuses: surface a warning but don't redirect automatically
      console.warn('Failed to fetch user profile', res.status, res.statusText);
      return null;
    }

    const user = await res.json();
    // Set global state so the rest of the app can react
    globalState.user = user;
    return user;
  } catch (err) {
    console.error('Error while fetching user profile', err);
    return null;
  }
}

export default fetchUserProfile;
