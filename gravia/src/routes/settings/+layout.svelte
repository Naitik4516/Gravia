<script lang="ts">
    import type { LayoutProps } from "./$types";
    import Sidebar from "$lib/components/settings/Sidebar.svelte";

    let { children }: LayoutProps = $props();
</script>

<div class="relative flex p-4 gap-5 bg-[#0A0B10]">
    <aside class="sidebar">
        <Sidebar />
    </aside>
    <main
        class="bg-[#FDFEFF]/3 w-full py-5 rounded-xl shadow-lg backdrop-blur-xl "
    >
        {@render children()}
    </main>
    <div class="absolute bottom-1/4 left-1/2 size-72 bg-[#05FF0D]/50 rounded-full blur-[180px] pointer-events-none"></div>
</div>
