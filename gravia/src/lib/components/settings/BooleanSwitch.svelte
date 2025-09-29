<script lang="ts">
  import { Switch } from '$lib/components/ui/switch';
  import { createEventDispatcher } from 'svelte';
  export let value: boolean;
  export let disabled: boolean = false;
  const dispatch = createEventDispatcher<{ change: boolean }>();

  function toggle() {
    if (disabled) return;
    const next = !value;
    // optimistic local update for immediate UI feedback
    value = next;
    dispatch('change', next);
  }
</script>

<Switch bind:checked={value} disabled={disabled} onclick={toggle} />

<style>
  :global(button[role="switch"]) { cursor: pointer; }
</style>
