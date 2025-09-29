import { writable } from 'svelte/store';
import { settingsCategoryUrl, SETTINGS_UPDATE_URL } from '$lib/constants/api';

const CONVERSATION_SETTINGS_URL = settingsCategoryUrl('conversation');

export interface ConversationSettings {
  auto_send_transcription: boolean;
  auto_capture_screen?: boolean;
}

function createConversationSettingsStore() {
  const { subscribe, set, update } = writable<ConversationSettings>({
    auto_send_transcription: false,
    auto_capture_screen: false,
  });

  async function fetchSettings() {
    try {
  const response = await fetch(CONVERSATION_SETTINGS_URL);
      if (response.ok) {
        const settings = await response.json() as ConversationSettings;
        set(settings);
      } else {
        console.error('Failed to fetch conversation settings');
      }
    } catch (error) {
      console.error('Error fetching conversation settings:', error);
    }
  }

  async function updateSettings(newSettings: Partial<ConversationSettings>) {
    try {
  const response = await fetch(SETTINGS_UPDATE_URL, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSettings),
      });
      if (response.ok) {
        const updatedSettings = await response.json() as ConversationSettings;
        set(updatedSettings);
      } else {
        console.error('Failed to update conversation settings');
      }
    } catch (error) {
      console.error('Error updating conversation settings:', error);
    }
  }

  return {
    subscribe,
    fetch: fetchSettings,
    update: updateSettings,
    set,
  };
}

export const conversationSettings = createConversationSettingsStore();

