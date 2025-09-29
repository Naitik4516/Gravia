<script lang="ts">
    import type { SettingItem } from "$lib/settings";
    import { Switch } from "$lib/components/ui/switch";
    import * as Select from "$lib/components/ui/select/index.js";
    import Button from "$lib/components/ui/button/button.svelte";
    import { cn } from "$lib/utils";
    import { tick } from "svelte";
    import * as Popover from "$lib/components/ui/popover/index.js";
    import CheckIcon from "@lucide/svelte/icons/check";
    import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
    import { toast } from "svelte-sonner";
    import * as Command from "$lib/components/ui/command/index.js";
    import {
        enable as enableAutostart,
        disable as disableAutostart,
    } from "@tauri-apps/plugin-autostart";
    import {
        register as registerShortcut,
        unregister as unregisterShortcut,
        isRegistered as isShortcutRegistered,
    } from "@tauri-apps/plugin-global-shortcut";
    import {
        integrationConnectUrl,
        integrationDisconnectUrl,
    } from "$lib/constants/api";

    interface Props {
        item: SettingItem;
        voiceOptions: { value: string; label: string }[];
        updateChanges: (
            key: string,
            value: any,
            manual?: boolean,
        ) => Promise<void>;
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
        voiceOptions,
        updateChanges,
        integrationLoading,
        capturingShortcut,
        capturingKeys,
        drafts,
        category,
        onShortcutCapture,
        onShortcutBlur,
    }: Props = $props();

    // Create reactive value for binding
    let value = $state(item.value);

    // Update value when item changes
    $effect(() => {
        value = item.value;
    });

    // Dynamic voices for combobox fields
    type Option = { value: string; label: string };

    function formatLabel(str: string) {
        return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function onInput(item: SettingItem, ev: Event) {
        const target = ev.target as
            | HTMLInputElement
            | HTMLSelectElement
            | HTMLTextAreaElement;
        let newValue: any = target.value;
        if (item.type === "boolean" || item.type === "toggle")
            newValue = (target as HTMLInputElement).checked;
        else if (item.type === "number") newValue = Number(newValue);
        value = newValue;
        const manual = ["string", "password", "number", "text"].includes(item.type);
        updateChanges(item.key, newValue, manual);
    }

    async function onToggleClick(item: SettingItem, current: boolean) {
        const newVal = !current;
        if (item.key === "auto_start") {
            try {
                if (newVal) await enableAutostart();
                else await disableAutostart();
                toast.success(
                    newVal ? "Auto-start enabled" : "Auto-start disabled",
                );
            } catch (e) {
                console.error("Auto-start error", e);
                toast.error("Failed to update auto-start");
                return;
            }
        }
        value = newVal;
        updateChanges(item.key, newVal, false);
    }

    function commitDraft(item: SettingItem) {
        const raw = (drafts[item.key] || "").trim();
        if (!raw) return;
        const current = Array.isArray(value) ? value : [];
        if (!current.includes(raw)) {
            const next = [...current, raw];
            value = next;
            updateChanges(item.key, next);
        }
        drafts[item.key] = "";
    }

    function removeTag(item: SettingItem, tag: string) {
        const current = (value || []).filter((t: string) => t !== tag);
        value = current;
        updateChanges(item.key, current);
    }

    function handleChipKey(item: SettingItem, e: KeyboardEvent) {
        if (e.key === "Enter" || e.key === ",") {
            e.preventDefault();
            commitDraft(item);
        } else if (e.key === "Backspace" && !drafts[item.key]) {
            const arr = Array.isArray(value) ? value : [];
            const newValue = arr.slice(0, -1);
            value = newValue;
            updateChanges(item.key, newValue, true);
        }
    }

    function handleChipPaste(item: SettingItem, e: ClipboardEvent) {
        const text = e.clipboardData?.getData("text") || "";
        if (!text) return;
        e.preventDefault();
        const parts = text
            .split(/[,\n]/)
            .map((p) => p.trim())
            .filter(Boolean);
        if (!parts.length) return;
        const existing = new Set(Array.isArray(value) ? value : []);
        const merged = [...existing, ...parts.filter((p) => !existing.has(p))];
        value = merged;
        updateChanges(item.key, merged, true);
        drafts[item.key] = "";
    }

    function formatShortcut(keys: string[]) {
        return keys.join(" + ");
    }

    async function onShortcutInput(item: SettingItem, ev: KeyboardEvent) {
        ev.preventDefault();
        if (ev.repeat) return;

        if (ev.key === "Escape") {
            onShortcutBlur(item.key);
            return;
        }

        const keys: string[] = [];
        if (ev.ctrlKey) keys.push("Ctrl");
        if (ev.altKey) keys.push("Alt");
        if (ev.shiftKey) keys.push("Shift");
        if (ev.metaKey) keys.push("Win");

        const isModifierOnly = ["Control", "Alt", "Shift", "Meta"].includes(
            ev.key,
        );
        if (!isModifierOnly) {
            let main = ev.key;
            if (main === " ") main = "Space";
            else if (ev.code === "Space") main = "Space";
            else if (main.length === 1) main = main.toUpperCase();
            keys.push(main);

            await applyShortcutChange(item, keys);
            await tick();
            onShortcutBlur(item.key);
        }
    }

    function shortcutDisplay(item: SettingItem) {
        if (capturingShortcut === item.key && capturingKeys.length) {
            return formatShortcut(capturingKeys);
        }
        const v = value;
        if (Array.isArray(v) && v.length) return formatShortcut(v);
        if (typeof v === "string" && v) return v;
        return "Press shortcut...";
    }

    function toAccelerator(keys: string[]): string {
        const mapped = keys.map((k) => (k === "Win" ? "Super" : k));
        return mapped.join("+");
    }

    async function applyShortcutChange(item: SettingItem, keys: string[]) {
        const prev = value;
        value = keys;
        updateChanges(item.key, keys, true);
        if (category !== "keyboard_shortcuts") return;

        const prevStr = Array.isArray(prev)
            ? toAccelerator(prev)
            : typeof prev === "string"
              ? prev
              : "";
        const nextStr = toAccelerator(keys);

        try {
            if (prevStr) {
                const reg = await isShortcutRegistered(prevStr);
                if (reg) await unregisterShortcut(prevStr);
            }
            if (nextStr) {
                await registerShortcut(nextStr, () => {
                    console.log(`Shortcut ${nextStr} triggered`);
                });
                toast.success(`Registered ${nextStr}`);
            }
        } catch (e) {
            console.error("Shortcut registration error", e);
            toast.error("Failed to register shortcut");
        }
    }

    async function connectIntegration(item: SettingItem) {
        integrationLoading[item.key] = true;
        try {
            const res = await fetch(integrationConnectUrl(item.key), {
                method: "POST",
            });
            if (!res.ok) throw new Error(await res.text());
            value = true;
            updateChanges(item.key, true, false);
            toast.success("Connected");
        } catch (e) {
            toast.error("Failed to connect");
        } finally {
            integrationLoading[item.key] = false;
        }
    }

    async function disconnectIntegration(item: SettingItem) {
        integrationLoading[item.key] = true;
        try {
            const res = await fetch(integrationDisconnectUrl(item.key), {
                method: "POST",
            });
            if (!res.ok) throw new Error(await res.text());
            value = false;
            updateChanges(item.key, false, false);
            toast.success("Disconnected");
        } catch (e) {
            toast.error("Failed to disconnect");
        } finally {
            integrationLoading[item.key] = false;
        }
    }

    function optionsFor(item: SettingItem): Option[] {
        if (
            item.options === "dynamic_voices" ||
            (item as any).dynamic_options === "voices"
        )
            return voiceOptions;
        const opts = Array.isArray(item.options) ? item.options : [];
        return opts.map((o) => ({ value: o, label: formatLabel(o) }));
    }
</script>

<div class="control">
    {#if item.type === "boolean" || item.type === "toggle"}
        <Switch checked={value} onclick={() => onToggleClick(item, value)} />
    {:else if item.type === "string" || item.type === "password"}
        <input
            type={item.type === "password" ? "password" : "text"}
            {value}
            oninput={(e) => onInput(item, e)}
        />
    {:else if item.type === "text"}
        <textarea
            rows="3"
            {value}
            oninput={(e) => onInput(item, e)}
        ></textarea>
    {:else if item.type === "number"}
        <input
            type="number"
            min={item.min}
            max={item.max}
            {value}
            oninput={(e) => onInput(item, e)}
        />
    {:else if item.type === "select"}
        <Select.Root
            type="single"
            bind:value
            onValueChange={(v: string) => {
                value = v;
                updateChanges(item.key, v, false);
            }}
        >
            <Select.Trigger class="min-w-50">
                {formatLabel(value)}
            </Select.Trigger>
            <Select.Content>
                {#each item.options || [] as opt}
                    <Select.Item value={opt}>{formatLabel(opt)}</Select.Item>
                {/each}
            </Select.Content>
        </Select.Root>
        <select
            class="hidden"
            {value}
            onchange={(e) => {
                const newValue = (e.target as HTMLSelectElement).value;
                value = newValue;
                updateChanges(item.key, newValue, false);
            }}
        >
            {#each item.options || [] as opt}
                <option value={opt}>{formatLabel(opt)}</option>
            {/each}
        </select>
    {:else if item.type === "combobox"}
        {#key item.key}
            {@const opts = optionsFor(item)}
            <Popover.Root>
                <Popover.Trigger>
                    {#snippet child({ props })}
                        <Button
                            {...props}
                            variant="outline"
                            class="bg-gray-900/40 hover:bg-gray-900/80 hover:text-white min-w-60 h-12 rounded-xl justify-between"
                            role="combobox"
                            aria-expanded="false"
                        >
                            {opts.find((o) => o.value === value)?.label ||
                                "Select..."}
                            <ChevronsUpDownIcon class="opacity-50" />
                        </Button>
                    {/snippet}
                </Popover.Trigger>
                <Popover.Content class="w-[240px] p-0">
                    <Command.Root>
                        <Command.Input placeholder="Search..." />
                        <Command.List>
                            <Command.Empty>No results.</Command.Empty>
                            <Command.Group value="options">
                                {#each opts as opt (opt.value)}
                                    <Command.Item
                                        value={opt.value}
                                        onSelect={() => {
                                            value = opt.value;
                                            updateChanges(
                                                item.key,
                                                opt.value,
                                                false,
                                            );
                                        }}
                                    >
                                        <CheckIcon
                                            class={cn(
                                                value !== opt.value &&
                                                    "text-transparent",
                                            )}
                                        />
                                        {opt.label}
                                    </Command.Item>
                                {/each}
                            </Command.Group>
                        </Command.List>
                    </Command.Root>
                </Popover.Content>
            </Popover.Root>
        {/key}
        <select
            class="hidden"
            value={item.value}
            onchange={(e) =>
                updateChanges(
                    item.key,
                    (e.target as HTMLSelectElement).value,
                    false,
                )}
        >
            {#each optionsFor(item) as o}
                <option value={o.value}>{o.label}</option>
            {/each}
        </select>
    {:else if item.type === "integration"}
        <Button
            disabled={integrationLoading[item.key]}
            onclick={() =>
                value ? disconnectIntegration(item) : connectIntegration(item)}
        >
            {integrationLoading[item.key]
                ? value
                    ? "Disconnecting..."
                    : "Connecting..."
                : value
                  ? "Disconnect"
                  : "Connect"}
        </Button>
    {:else if item.type === "list"}
        <div
            class="chip-wrapper"
            role="button"
            tabindex="0"
            onclick={() => (drafts[item.key] = drafts[item.key] || "")}
            onkeydown={(e: KeyboardEvent) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    drafts[item.key] = drafts[item.key] || "";
                }
            }}
        >
            {#each Array.isArray(value) ? value : [] as tag (tag)}
                <span class="chip"
                    >{tag}
                    <button
                        type="button"
                        class="text-xs hover:text-white text-gray-300 cursor-pointer"
                        onclick={(e) => {
                            e.stopPropagation();
                            removeTag(item, tag);
                        }}
                        aria-label="Remove tag"
                        >✖
                    </button>
                </span>
            {/each}
            <input
                class="chip-input"
                type="text"
                placeholder={Array.isArray(value) && value.length
                    ? ""
                    : "Add item"}
                value={drafts[item.key] || ""}
                oninput={(e) =>
                    (drafts[item.key] = (e.target as HTMLInputElement).value)}
                onkeydown={(e: KeyboardEvent) => handleChipKey(item, e)}
                onpaste={(e: ClipboardEvent) => handleChipPaste(item, e)}
            />
        </div>
    {:else if item.type === "shortcut"}
        <button
            class="shortcut-btn {capturingShortcut === item.key
                ? 'recording'
                : ''}"
            type="button"
            aria-pressed={capturingShortcut === item.key}
            aria-label="Shortcut capture button"
            aria-live="polite"
            onclick={() => onShortcutCapture(item.key)}
            onkeydown={(e) => onShortcutInput(item, e)}
            onblur={() => onShortcutBlur(item.key)}
        >
            {shortcutDisplay(item)}
        </button>
    {/if}
</div>

<style>
    :global(.control input[type="text"]),
    :global(.control input[type="password"]),
    :global(.control input[type="number"]) {
        background: #181e21;
        border: 1px solid #262e33;
        color: #fff;
        padding: 0.6rem 0.8rem;
        border-radius: 0.6rem;
        font-size: 0.9rem;
        min-width: 220px;
    }

    :global(.control textarea) {
        background: #181e21;
        border: 1px solid #262e33;
        color: #fff;
        padding: 0.6rem 0.8rem;
        border-radius: 0.6rem;
        font-size: 0.9rem;
        min-width: 220px;
        resize: vertical;
        font-family: inherit;
    }

    .chip-wrapper {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        align-items: center;
        min-width: 280px;
        background: #181e21;
        border: 1px solid #262e33;
        border-radius: 0.6rem;
        padding: 0.35rem 0.5rem;
        cursor: text;
    }

    .chip {
        background: #262e33;
        color: #fff;
        border-radius: 1rem;
        padding: 0.25rem 0.75rem 0.25rem 0.65rem;
        font-size: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.35rem;
        line-height: 1;
    }

    .chip-input {
        background: transparent;
        border: none;
        outline: none;
        color: #fff;
        min-width: 60px;
        font-size: 0.8rem;
        padding: 0.2rem 0.25rem;
    }

    .chip-input::placeholder {
        color: #666;
    }

    .shortcut-btn {
        background: #181e21;
        border: 1px solid #262e33;
        color: #fff;
        border-radius: 0.6rem;
        font-size: 0.95rem;
        min-width: 220px;
        padding: 0.6rem 0.8rem;
        cursor: pointer;
        outline: none;
        text-align: left;
    }

    .shortcut-btn:focus {
        border-color: #4f8cff;
        box-shadow: 0 0 0 2px #4f8cff44;
    }

    .shortcut-btn.recording {
        border-color: #7dd3fc;
        box-shadow: 0 0 0 2px #7dd3fc44;
        animation: pulse 1.1s ease-in-out infinite;
    }

    @keyframes pulse {
        0%,
        100% {
            background: #181e21;
        }
        50% {
            background: #1f262a;
        }
    }
</style>
