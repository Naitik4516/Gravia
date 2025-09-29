<script lang="ts">
    import { listen } from "@tauri-apps/api/event";
    import { onMount, onDestroy } from "svelte";

    let status = $state("");
    let unlisten: any;

    interface StatusEvent {
        type: "status";
        data: string;
    }

    onMount(async () => {
        unlisten = await listen<StatusEvent>("event", (event) => {
            console.log("Received event:", event);
            console.log("Event payload:", event.payload);
            if (event.payload.type === "status") {
                if (event.payload.data === "clear") {
                    status = "";
                } else {
                    status = event.payload.data;
                }
            }
        });
    });

    onDestroy(() => {
        unlisten();
    });
</script>

<div>
    <p class="fixed bottom-2 left-4 text-slate-400 font-[Tektur] tracking-wide capitalize">
        {status}
    </p>
</div>
