<script lang="ts">
    import { Trash2, X } from "@lucide/svelte";

    let { item, id, handleDelete, handleClearAll, loading, error } = $props();

    let hovering: Record<string, boolean> = $state({});

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

<div
    class=" relative border border-white/10 rounded-xl p-4 bg-white/5"
    onmouseenter={() => (hovering[id] = true)}
    onmouseleave={() => (hovering[id] = false)}
    role="region"
>
    <div class="flex items-center justify-between min-h-10">
        <h3 class="text-gray-200 font-semibold truncate">
            {item.session_name || "Untitled session"}
        </h3>
        {#if hovering[id]}
            <div class="flex items-center gap-2 ml-4">
                <button
                    class="text-red-400 hover:text-red-300 bg-red-400/10 hover:bg-red-400/20 rounded-full p-2"
                    aria-label="Delete session"
                    onclick={() => handleDelete(item.session_id)}
                >
                    <X class="w-4 h-4" />
                </button>
            </div>
        {:else}
            <div class="text-sm text-gray-200">
                {relativeTime(item.updated_at ?? item.created_at)}
            </div>
        {/if}
    </div>
</div>
