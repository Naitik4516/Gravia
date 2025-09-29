<script lang="ts">
    import type { SettingItem } from "$lib/settings";
    import SettingControl from "./SettingControl.svelte";

    interface Props {
        item: SettingItem;
        isChild?: boolean;
        voiceOptions: { value: string; label: string }[];
        updateChanges: (key: string, value: any, manual?: boolean) => Promise<void>;
        integrationLoading: Record<string, boolean>;
        capturingShortcut: string | null;
        capturingKeys: string[];
        drafts: Record<string, string>;
        category: string;
        onShortcutCapture: (key: string) => void;
        onShortcutBlur: (key: string) => void;
    }

    let {
        item,
        isChild = false,
        voiceOptions,
        updateChanges,
        integrationLoading,
        capturingShortcut,
        capturingKeys,
        drafts,
        category,
        onShortcutCapture,
        onShortcutBlur
    }: Props = $props();

</script>

<div
    class="setting-item {isChild ? 'child-setting' : 'parent-setting'}"
>
    <div class="info">
        <h3 class="setting-title {isChild ? 'child-title' : 'parent-title'}">
            {item.label}
        </h3>
        {#if item.description}
            <p class="setting-description {isChild ? 'child-description' : 'parent-description'}">
                {item.description}
            </p>
        {/if}
    </div>
    
    <SettingControl
        {item}
        {voiceOptions}
        {updateChanges}
        {integrationLoading}
        {capturingShortcut}
        {capturingKeys}
        {drafts}
        {category}
        {onShortcutCapture}
        {onShortcutBlur}
    />
</div>

<style>
    .setting-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        padding: 1.5rem 1.25rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    .parent-setting {
        background: rgba(255, 255, 255, 0.04);
        flex-direction: column;
        gap: 1rem;
    }

    .child-setting {
        background: rgba(255, 255, 255, 0.02);
        border-left: 2px solid rgba(16, 185, 129, 0.5);
        box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.05);
        flex-direction: row;
        padding: 1rem;
    }

    @media (min-width: 1024px) {
        .parent-setting {
            flex-direction: row;
            gap: 1rem;
        }
    }

    @media (max-width: 600px) {
        .setting-item {
            flex-direction: column;
            gap: 1rem;
            justify-content: flex-start;
            align-items: flex-start;
            
        }
    }

    .info {
        flex: 1;
    }

    .setting-title {
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    .parent-title {
        font-size: 1.25rem;
    }

    .child-title {
        font-size: 1.125rem;
        color: rgb(229, 231, 235);
    }

    .setting-description {
        font-weight: 300;
        line-height: 1.4;
    }

    .parent-description {
        font-size: 0.875rem;
    }

    .child-description {
        font-size: 0.75rem;
        color: rgb(156, 163, 175);
    }
</style>