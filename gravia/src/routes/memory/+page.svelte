<script lang="ts">
  import { onMount } from "svelte";
  import { listMemory, deleteMemory, clearMemory } from "$lib/chat/chatService";
  import { Trash2, X } from "@lucide/svelte";
  import type { PageProps } from "./$types";
  import {Button} from "$lib/components/ui/button";

  type Memory = {
    memory_id: string;
    memory: string;
    topics?: string[];
    input?: string;
    last_updated?: string;
  };

  let memories = $state<Memory[]>([]);
  let { data }: PageProps = $props();

  $effect(() => {
    memories = data?.memories || [];
  });

  async function handleDelete(id: string) {
    try {
      await deleteMemory(id);
      memories = memories.filter((m) => m.memory_id !== id);
    } catch {
      /* noop */
    }
  }

  async function handleClearAll() {
    if (!confirm("Are you sure you want me to forget everything? This cannot be undone.")) return;
    try {
      await clearMemory();
      memories = [];
    } catch {
      /* noop */
    }
  }
</script>

<div class="px-5 py-10 h-screen overflow-auto">
  <h1 class="text-5xl font-black text-gray-200 text-center">Memories & Moments</h1>
  <div class="w-full">
    <div class="flex items-center justify-end  max-w-4xl mx-auto mt-10">
      <Button
        onclick={handleClearAll}
        aria-label="Forget all Memories"
        title="Let go of everything"
        variant="destructive"
      >
        <Trash2 class="w-4 h-4" /> Forget All
      </Button>
    </div>
    <div
      class=" space-y-4 max-h-[calc(99vh-7rem)] inset-shadow-sm overflow-y-scroll mx-auto"
    >
      {#await data.memories}
        <div class="text-gray-200">Sifting through your memories…</div>
      {:then memories}
        {#if !memories || memories.length === 0}
          <div class="text-center space-y-3 mx-auto min-h-[calc(99vh-7rem)] flex flex-col justify-center items-center">
            <div class="text-3xl text-gray-200 font-['Rubik'] leading tracking-widest">Your memory garden is quiet.</div>
            <div class="text-sm text-gray-400 max-w-lg mx-auto px-4">It looks like you haven't planted any memories yet. Chat with your assistant to begin — every conversation can bloom into something worth remembering.</div>
          </div>
        {:else}
          <div class="grid gap-3 mx-auto max-w-4xl mt-5">
            {#each memories as m (m.memory_id)}
              <div
                class="relative border border-white/10 rounded-xl p-4 bg-white/5 hover:bg-slate-900/10 shadow-lg"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div
                      class="text-gray-200 font-medium whitespace-pre-wrap break-words"
                    >
                      {m.memory}
                    </div>
                    {#if m.topics?.length}
                      <div class="mt-2 flex flex-wrap gap-2">
                        {#each m.topics as t}
                          <span
                            class="text-xs bg-white/10 text-gray-300 px-2 py-0.5 rounded-full"
                            >{t}</span
                          >
                        {/each}
                      </div>
                    {/if}
                    {#if m.last_updated}
                      <div class="mt-1 text-xs text-gray-500">
                        Updated: {new Date(m.last_updated).toLocaleString()}
                      </div>
                    {/if}
                  </div>
                  <button
                    class="text-red-400 hover:text-red-300 bg-red-400/10 hover:bg-red-400/20 rounded-full p-2"
                    aria-label="Delete memory"
                    onclick={() => handleDelete(m.memory_id)}
                  >
                    <X class="w-4 h-4" />
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      {:catch error}
        <div class="text-red-400">Hmm — something went sideways: {error.message || error}</div>
      {/await}
    </div>
  </div>
</div>
