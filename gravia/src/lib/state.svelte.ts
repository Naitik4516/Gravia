import type { User, windowMode } from "./types"
import type { Message } from "./chat/types";
import { getCurrentWindow, LogicalSize } from '@tauri-apps/api/window';
import { moveWindow, Position } from '@tauri-apps/plugin-positioner';


export let globalState = $state({
    // null when not loaded / not authenticated
    user: null as User | null,
    windowMode: 'default',
    lastAssistantMessage: null as Message | null,
})

export function setLastAssistantMessage(message: Message) {
    if (message.role === 'assistant' && message.content) {
        globalState.lastAssistantMessage = message;
    }
}


export async function toggleWindowMode() {
    globalState.windowMode = globalState.windowMode === 'default' ? 'mini' : 'default';

    const appWindow = getCurrentWindow();
    if (globalState.windowMode === 'mini') {
        moveWindow(Position.BottomRight)
        appWindow.setSize(new LogicalSize(400, 500));
        appWindow.setAlwaysOnTop(true);
        appWindow.setSkipTaskbar(true);
        appWindow.setFocus();
    }
    else {
        moveWindow(Position.Center);
        appWindow.setSize(new LogicalSize(1100, 700));
        appWindow.setAlwaysOnTop(false);
        appWindow.setSkipTaskbar(false);
        appWindow.setFocus();
    }

}