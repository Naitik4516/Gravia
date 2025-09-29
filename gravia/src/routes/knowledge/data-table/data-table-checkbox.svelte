<script lang="ts">
  import type { ComponentProps } from 'svelte';
  import { Checkbox } from '$lib/components/ui/checkbox/index.js';

  let { checked = false, indeterminate = false, onCheckedChange = (v:boolean)=>{}, ...rest }: ComponentProps<typeof Checkbox> & { indeterminate?: boolean; onCheckedChange?: (v:boolean)=>void } = $props();
</script>

<Checkbox bind:checked {indeterminate}  class="bg-gray-700/50 hover:bg-gray-800 cursor-pointer" onCheckedChange={(v: any) => onCheckedChange(!!v)} {...rest} />
