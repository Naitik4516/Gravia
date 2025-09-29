<script lang="ts">
    import { clearAllSessions, deleteSession } from "$lib/chat/chatService";
    import { Trash2, X } from "@lucide/svelte";
    import type { PageProps } from "./$types";
    import { toast } from "svelte-sonner";

    let { data }: PageProps = $props();

    type Session = {
        session_id: string;
        user_id?: string;
        session_name?: string | null;
        created_at?: number | string | null;
        updated_at?: number | string | null;
    };

    let sessions = $state<Session[]>([]);
    let expanded: Record<string, boolean> = $state({});
    let histories: Record<string, any> = $state({});
    let hovering: Record<string, boolean> = $state({});

    async function handleDelete(id: string) {
        try {
            await deleteSession(id);
            sessions = sessions.filter((s) => s.session_id !== id);
            delete histories[id];
            delete expanded[id];
            toast.success("Session deleted");
        } catch (e) {
            console.error(e);
            toast.error("Failed to delete session");
        }
    }

    async function handleClearAll() {
        if (!confirm("Delete all sessions?")) return;
        try {
            await clearAllSessions();
            sessions = [];
            histories = {};
            expanded = {};
            toast.success("All sessions deleted");
        } catch (e) {
            toast.error("Failed to delete all sessions");
        }
    }

    // New: relative time formatter (prefers seconds input; supports string dates)
    function relativeTime(t?: number | string | null) {
        if (!t && t !== 0) return "";
        try {
            const ms = typeof t === "number" ? t * 1000 : new Date(t).getTime();
            const now = Date.now();
            let diff = Math.max(0, now - ms);

            const sec = Math.floor(diff / 1000);
            if (sec < 60) return `${sec} sec${sec !== 1 ? "s" : ""} ago`;

            const min = Math.floor(sec / 60);
            if (min < 60) return `${min} min${min !== 1 ? "s" : ""} ago`;

            const hr = Math.floor(min / 60);
            if (hr < 24) return `${hr} hour${hr !== 1 ? "s" : ""} ago`;

            const day = Math.floor(hr / 24);
            if (day < 7) return `${day} day${day !== 1 ? "s" : ""} ago`;

            const week = Math.floor(day / 7);
            if (week < 5) return `${week} week${week !== 1 ? "s" : ""} ago`;

            const month = Math.floor(day / 30);
            if (month < 12)
                return `${month} month${month !== 1 ? "s" : ""} ago`;

            const year = Math.floor(day / 365);
            return `${year} year${year !== 1 ? "s" : ""} ago`;
        } catch {
            return "";
        }
    }
</script>

<div class="px-5 py-6 h-screen overflow-auto">
    <div class="w-full">
        <div class="flex items-center justify-between mb-8 w-4/5 mx-auto">
            <h1 class="text-4xl font-bold text-gray-200 ">Chat Sessions</h1>
            <button
                class="flex items-center gap-2 text-red-300 hover:text-red-200 bg-red-500/10 hover:bg-red-500/20 px-3 py-1.5 rounded-md"
                onclick={handleClearAll}
                aria-label="Clear all sessions"
            >
                <Trash2 class="w-4 h-4" /> Delete All
            </button>
        </div>
        <div class=" space-y-4 max-h-[calc(99vh-7rem)] inset-shadow-sm overflow-y-scroll mx-auto">
            {#await data.sessions}
                <div class="text-gray-300">Loading…</div>
            {:then sessions}
                {#if sessions.length === 0}
                    <div class="text-gray-400">No sessions yet.</div>
                {:else}
                    <div class="space-y-3 mx-auto max-w-4xl pb-5">
                        {#each sessions as s (s.session_id)}
                            <div
                                class="border border-white/10 rounded-xl p-4 bg-white/5"
                                onmouseenter={() =>
                                    (hovering[s.session_id] = true)}
                                onmouseleave={() =>
                                    (hovering[s.session_id] = false)}
                                role="region"
                            >
                                <a
                                    class="flex items-center justify-between min-h-10 cursor-pointer"
                                    href={`/?sessionId=${s.session_id}`}
                                    onclick={() => sessionStorage.setItem("sessionId", s.session_id)}
                                    >
                                    <h3
                                        class="text-gray-200 font-semibold truncate"
                                    >
                                        {s.session_name || "Untitled session"}
                                    </h3>
                                    {#if hovering[s.session_id]}
                                        <div
                                            class="flex items-center gap-2 ml-4"
                                        >
                                            <button
                                                class="text-red-400 hover:text-red-300 bg-red-400/10 hover:bg-red-400/20 rounded-full p-2"
                                                aria-label="Delete session"
                                                onclick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    handleDelete(s.session_id);
                                                }}
                                            >
                                                <X class="w-4 h-4" />
                                            </button>
                                        </div>
                                    {:else}
                                        <div class="text-sm text-gray-200">
                                            {relativeTime(
                                                s.updated_at ?? s.created_at,
                                            )}
                                        </div>
                                    {/if}
                                </a>
                            </div>
                        {/each}
                        <div class="absolute bottom-6 left-0 right-0 h-16 max-w-4xl mx-auto bg-gradient-to-t from-gray-950 to-transparent pointer-events-none"></div>
                    </div>
                {/if}
            {:catch error}
                <div class="text-red-400">{error.message || error}</div>
            {/await}
        </div>
    </div>
</div>
