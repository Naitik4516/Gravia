import { defaultWindowIcon } from "@tauri-apps/api/app";
import { Menu } from "@tauri-apps/api/menu";
import { TrayIcon } from "@tauri-apps/api/tray";
import type { ServerInit } from '@sveltejs/kit';
import { register as registerShortcut, isRegistered as isShortcutRegistered, unregister as unregisterShortcut } from '@tauri-apps/plugin-global-shortcut';
import { exit, relaunch } from '@tauri-apps/plugin-process';
import { getCurrentWindow, Window } from '@tauri-apps/api/window';
import { toggleWindowMode } from '$lib/state.svelte';
import { chatClient } from '$lib/chat/chatService';
import { globalState } from '$lib/state.svelte';
import { settingsCategoryUrl } from '$lib/constants/api';
import { once } from '@tauri-apps/api/event';

const registerShortcuts = async () => {
    try {
        const res = await fetch(settingsCategoryUrl('keyboard_shortcuts'));
        console.log('Fetched keyboard shortcuts:', res);
        if (res.ok) {
            const payload = await res.json();
            const settings = Array.isArray(payload?.settings) ? payload.settings : payload;
            const shortcuts = (settings || []).filter((s: any) =>
                typeof s?.key === 'string' &&
                /shortcut$/i.test(s.key) &&
                typeof s.value === 'string' &&
                s.value.length > 0
            );

            console.log("Payload:", payload);
            console.log('Registering shortcuts:', shortcuts);

            for (const sc of shortcuts) {
                const accel = sc.value.replace(/Win/g, 'Super');
                console.log('Registering shortcut', accel);
                try {
                    const reg = await isShortcutRegistered(accel);
                    if (reg) await unregisterShortcut(accel);
                    await registerShortcut(accel, (event) => {
                        if (event.state === "Pressed") {
                            console.log(`Shortcut ${accel} triggered`);
                            switch (sc.key) {
                                case 'mini_window_shortcut':
                                    toggleWindowMode();
                                    break;
                                case 'toggle_listening_shortcut':
                                    chatClient.toggleListening();
                                    break;
                                case 'push_to_talk_shortcut':
                                    chatClient.startListening();
                                    break;
                                case 'speak_last_response_shortcut':
                                    if (globalState.lastAssistantMessage?.content) {
                                        chatClient.speak(globalState.lastAssistantMessage.content);
                                    }
                                    break;
                            }
                        } else if (event.state === "Released") {
                            switch (sc.key) {
                                case 'push_to_talk_shortcut':
                                    chatClient.stopListening();
                                    break;
                            }
                        }
                    });
                    console.log('Registered shortcut', accel);
                } catch (e) {
                    console.error('Error registering shortcut', accel, e);
                }
            }
        }
    } catch (e) {
        console.error('Failed to load keyboard shortcuts', e);
    }
}

export const init: ServerInit = async () => {
    const appWindow = getCurrentWindow();

    const menu = await Menu.new({
        items: [
            {
                id: "quit",
                text: "Quit",
                action: async () => {
                    await exit(0);
                }
            },
            {
                id: "restart",
                text: "Restart",
                action: async () => {
                    await relaunch();
                }
            }
        ],
    });

    const iconCandidate = await defaultWindowIcon();
    const options = {
        icon: iconCandidate || '',
        menu,
        menuOnLeftClick: false,
        action: (event) => {
            switch (event.type) {
                case 'Click':
                    console.log(`mouse ${event.button} button pressed`);
                    if (event.button !== 'Left') break;
                    appWindow.unminimize();
                    appWindow.show();
                    appWindow.setFocus();
                    break;
                case 'DoubleClick':
                    console.log(`mouse ${event.button} button pressed`);
                    break;
            }
        }
    };

    const tray = await TrayIcon.new(options);


    await once('server-ready', async (_event) => {
        const splashscreen = await Window.getByLabel("splashscreen");
        const mainWindow = await Window.getByLabel("main");
        splashscreen?.close();
        mainWindow?.show();
        await registerShortcuts();
    });


};