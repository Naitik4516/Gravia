<script lang="ts">
    import type { PageProps } from "./$types";
    import type { SettingItem } from "$lib/settings";
    import { shouldShowField, createParentValueMap } from "$lib/settings";
    import { toast } from "svelte-sonner";
    import { invalidate } from "$app/navigation";
    import {
        settingsCategoryUrl,
        SETTINGS_UPDATE_URL,
        SETTINGS_UPDATE_CATEGORY_URL,
        SETTINGS_VOICES_URL,
    } from "$lib/constants/api";
    import Button from "$lib/components/ui/button/button.svelte";
    import SettingItemComponent from "$lib/components/settings/SettingItem.svelte";

    let { data }: PageProps = $props();
    let category = $derived(data.category || "general");
    let rawSettings = $derived(data.settings);

    // Add parent-child relationships to settings
    let settings = $derived(
        rawSettings.map((setting: any) => {
            // Add parent-child relationships based on the setting key
            if (setting.key === "thinking_budget_primary") {
                return {
                    ...setting,
                    parent: "primary_model",
                    condition: ["gemini-2.5-flash", "gemini-2.5-flash-lite"],
                    condition_type: "in",
                };
            } else if (setting.key === "thinking_budget_reasoning") {
                return {
                    ...setting,
                    parent: "reasoning_model",
                    condition: "gemini-2.5-pro",
                    condition_type: "equals",
                };
            }
            return setting;
        }),
    );
    let changes = $state(false);
    let capturingShortcut: string | null = $state(null);
    let capturingKeys: string[] = $state([]);
    let integrationLoading: Record<string, boolean> = $state({});
    let drafts: Record<string, string> = $state({});

    // Dynamic voices for combobox fields
    type Option = { value: string; label: string };
    let voiceOptions: Option[] = $state([]);
    let voicesLoaded = $state(false);
    let voicesError: string | null = $state(null);

    $effect(() => {
        const needsVoices = settings.some(
            (s: SettingItem) =>
                s.type === "combobox" &&
                (s.options === "dynamic_voices" ||
                    (s as any).dynamic_options === "voices"),
        );
        if (!needsVoices || voicesLoaded) return;
    fetch(SETTINGS_VOICES_URL)
            .then((r) => r.json())
            .then((data) => {
                const raw = Array.isArray(data)
                    ? data
                    : Array.isArray((data as any)?.voices)
                      ? (data as any).voices
                      : [];
                voiceOptions = raw.map((it: any) => {
                    if (typeof it === "string")
                        return { value: it, label: it } as Option;
                    if (it && typeof it === "object") {
                        const value =
                            it.short_name ?? it.value ?? it.id ?? it.name ?? "";
                        const label =
                            it.short_name.split("-").pop() +
                            ` (${it.locale}, ${it.gender})`;
                        return { value, label } as Option;
                    }
                    return { value: String(it), label: String(it) } as Option;
                });
                voicesLoaded = true;
            })
            .catch((e) => {
                voicesError = String(e);
                voicesLoaded = true;
            });
    });

    // Create a reactive map of parent values for condition evaluation
    let parentValues = $derived(createParentValueMap(settings));

    // Organize settings into a hierarchical structure
    let organizedSettings = $derived.by(() => {
        const visible = settings.filter((setting: SettingItem) =>
            shouldShowField(setting, parentValues),
        );
        const parents: SettingItem[] = [];
        const children: Record<string, SettingItem[]> = {};

        // Separate parent and child fields
        visible.forEach((setting: SettingItem) => {
            if (setting.parent) {
                if (!children[setting.parent]) {
                    children[setting.parent] = [];
                }
                children[setting.parent].push(setting);
            } else {
                parents.push(setting);
            }
        });

        return { parents, children };
    });

    async function updateChanges(key: string, value: any, manual = true) {
        changes = manual;
        settings = settings.map((s: SettingItem) =>
            s.key === key ? { ...s, value } : s,
        );
        if (!manual) {
            try {
                const res = await fetch(SETTINGS_UPDATE_URL, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ category, key, value }),
                });
                if (!res.ok) {
                    console.error('Failed to update setting', key);
                } else {
                    // If we've updated the conversation category, refresh the conversationSettings store
                    if (category === 'conversation') {
                        try {
                            // Importing here avoids a top-level cycle for routes that don't need the store
                            const { conversationSettings } = await import('$lib/stores/conversation');
                            // Refresh remote settings into the store so subscribers pick up changes
                            conversationSettings.fetch().catch((e: any) => console.warn('Failed to refresh conversation settings', e));
                        } catch (e) {
                            console.warn('Could not refresh conversation settings store', e);
                        }
                    }
                }
            } catch (err) {
                console.error('Error updating setting:', err);
            }
        }
    }

    const handleSave = () => {
        if (changes) {
            changes = false;
            fetch(SETTINGS_UPDATE_CATEGORY_URL, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ category, settings }),
            })
                .then(() => {
                    toast.success("Settings updated");
                })
                .catch((error) => {
                    toast.error("Failed to save");
                    console.error("Error updating settings:", error);
                });
            invalidate(settingsCategoryUrl(category));
        }
    };

    function onShortcutCapture(key: string) {
        capturingShortcut = key;
        capturingKeys = [];
    }

    function onShortcutBlur(key: string) {
        if (capturingShortcut === key) {
            capturingShortcut = null;
            capturingKeys = [];
        }
    }

    function formatLabel(str: string) {
        return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }
</script>

<section class="section">
    <header class="flex justify-between mx-10">
        <h1 class="font-bold text-5xl font-['Orbitron'] mb-8">
            {formatLabel(category)}
        </h1>
        <Button
            class="bg-emerald-400 rounded-lg hover:bg-emerald-500 {!changes &&
                'hidden'}"
            onclick={handleSave}>Save</Button
        >
    </header>
    <div class="flex flex-col gap-5 overflow-y-auto max-h-[79vh] px-8 pb-4">
        {#each organizedSettings.parents as item (item.key)}
            <div class="setting-group">
                <!-- Parent field -->
                <SettingItemComponent
                    {item}
                    isChild={false}
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

                <!-- Child fields -->
                {#if organizedSettings.children[item.key] && organizedSettings.children[item.key].length > 0}
                    <div class="child-fields ml-8 mt-3 space-y-3">
                        {#each organizedSettings.children[item.key] as childItem (childItem.key)}
                            <SettingItemComponent
                                item={childItem}
                                isChild={true}
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
                        {/each}
                    </div>
                {/if}
            </div>
        {/each}
    </div>
</section>

<style>
    .setting-group {
        display: flex;
        flex-direction: column;
    }

    .child-fields {
        position: relative;
    }

    .child-fields::before {
        content: "";
        position: absolute;
        left: -1rem;
        top: 0;
        bottom: 0;
        width: 2px;
        background: linear-gradient(
            to bottom,
            transparent,
            #10b981,
            transparent
        );
        opacity: 0.3;
    }
</style>
