import { conversationSettings } from '$lib/stores/conversation';

export const load = async () => {
  try {
    await conversationSettings.fetch();
  } catch (error) {
    console.warn('Failed to load conversation settings:', error);
    // Return empty object to prevent preloading failures
    return {};
  }
};
