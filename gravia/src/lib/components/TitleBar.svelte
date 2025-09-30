<script lang="ts">
    import {
        Square,
        X,
        Minus,
        PictureInPicture,
        SquareArrowOutUpLeft,
    } from "@lucide/svelte";
    import MenuBar from "$lib/components/MenuBar.svelte";
    import { getCurrentWindow } from "@tauri-apps/api/window";
    import { onMount } from "svelte";
    import { globalState, toggleWindowMode } from "$lib/state.svelte";
    import { emit } from '@tauri-apps/api/event';


    const window = getCurrentWindow();

    let isMaximized = $state(false);

    async function checkWindowState() {
        const _isMaximized = await window.isMaximized();
        isMaximized = _isMaximized;
    }

    onMount(() => {
        document
            .getElementById("titlebar")
            ?.addEventListener("mousedown", (e) => {
                if (e.buttons === 1) {
                    // Primary (left) button
                    const target = e.target as HTMLElement; // Add type assertion
                    if (target.id === "titlebar") {
                        e.detail === 2
                            ? window.toggleMaximize() // Maximize on double click
                            : window.startDragging(); // Else start dragging
                    }
                }
            });
        window.listen("tauri://resize", () => {
            checkWindowState();
        });
    });

    const toggleMaximize = async () => {
        console.log("Toggling maximize");
        if (isMaximized) {
            await window.unmaximize();
        } else {
            await window.maximize();
        }
    };

    const close = async () => {
        console.log("Closing window");
        // await window.close();
        await emit('app-close');
    };

    const minimize = async () => {
        console.log("Minimizing window");
        await window.minimize();
    };
</script>

<nav
    id="titlebar"
    class="fixed top-0 left-0 right-0 flex items-center justify-center px-4 z-20 h-10"
>
    {#if globalState.windowMode === "default"}
        <div class="absolute left-3 top-2">
            <MenuBar />
        </div>
    {/if}
    <div class="absolute right-2 top-1/2 -translate-y-1/2 flex controls">
        <button
            id="titlebar-toggle-window-mode"
            title="toggle window mode"
            onclick={toggleWindowMode}
        >
            {#if globalState.windowMode === "default"}
                <PictureInPicture class="w-5 h-5" />
            {:else}
                <SquareArrowOutUpLeft class="w-5 h-5" />
            {/if}
        </button>
        {#if globalState.windowMode === "default"}
            <button id="titlebar-minimize" title="minimize" onclick={minimize}>
                <Minus class="w-5 h-5" />
            </button>
            <button
                id="titlebar-maximize"
                title="maximize"
                onclick={toggleMaximize}
            >
                {#if !isMaximized}
                    <Square class="w-4 h-4" />
                {:else}
                    <svg
                        width="20px"
                        height="20px"
                        viewBox="0 0 16 16"
                        fill="white"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        <path
                            d="M5.08496 4C5.29088 3.4174 5.8465 3 6.49961 3H9.99961C11.6565 3 12.9996 4.34315 12.9996 6V9.5C12.9996 10.1531 12.5822 10.7087 11.9996 10.9146V6C11.9996 4.89543 11.1042 4 9.99961 4H5.08496Z"
                            fill="#fff"
                        />
                        <path
                            d="M4.5 5H9.5C10.3284 5 11 5.67157 11 6.5V11.5C11 12.3284 10.3284 13 9.5 13H4.5C3.67157 13 3 12.3284 3 11.5V6.5C3 5.67157 3.67157 5 4.5 5ZM4.5 6C4.22386 6 4 6.22386 4 6.5V11.5C4 11.7761 4.22386 12 4.5 12H9.5C9.77614 12 10 11.7761 10 11.5V6.5C10 6.22386 9.77614 6 9.5 6H4.5Z"
                            fill="#fff"
                        />
                    </svg>
                {/if}
            </button>
        {/if}
        <button id="titlebar-close" title="close" onclick={close}>
            <X class="w-5 h-5" />
        </button>
    </div>
</nav>

<style>
    .controls button {
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        margin-left: 0.25rem;
        padding: 0.25rem;
        color: var(--text-primary);
    }

    .controls button:hover {
        background-color: #465268c7;
        color: white;
    }

    .controls button:active {
        background-color: var(--bg-accent);
    }

    .controls button#titlebar-close:hover {
        background-color: #e81123;
    }

    .controls button#titlebar-close:active {
        background-color: #f1707a;
    }
</style>
