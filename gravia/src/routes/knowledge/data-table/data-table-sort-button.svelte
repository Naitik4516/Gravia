<script lang="ts">
    import type { ComponentProps } from "svelte";
    import type { Snippet } from "svelte";
    import ArrowUpDownIcon from "@lucide/svelte/icons/arrow-up-down";
    import ArrowUpIcon from "@lucide/svelte/icons/arrow-up";
    import ArrowDownIcon from "@lucide/svelte/icons/arrow-down";
    import { Button } from "$lib/components/ui/button/index.js";
    
    let {
        children,
        variant = "ghost",
        sortDirection,
        ...rest
    }: ComponentProps<typeof Button> & {
        sortDirection?: 'asc' | 'desc' | false;
        children: Snippet;
    } = $props();
</script>

<Button {variant} {...rest} class="pl-2 pr-2 h-8 text-xs font-medium hover:bg-neutral-800">
    {@render children()}
    {#if sortDirection === 'asc'}
        <ArrowUpIcon class="ml-1 size-3.5" />
        <span class="sr-only">Sorted ascending</span>
    {:else if sortDirection === 'desc'}
        <ArrowDownIcon class="ml-1 size-3.5" />
        <span class="sr-only">Sorted descending</span>
    {:else}
        <ArrowUpDownIcon class="ml-1 size-3.5" />
        <span class="sr-only">Toggle sort</span>
    {/if}
</Button>
