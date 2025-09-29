<script lang="ts">
  import TitleBar from "$lib/components/TitleBar.svelte";
  import { Toaster } from "$lib/components/ui/sonner/index.js";
  import type { LayoutProps } from "./$types";
  import { onMount } from 'svelte';
  import { fetchUserProfile } from '$lib/auth';



  import "../app.css";

  let { children }: LayoutProps = $props();

  onMount(() => {
    // Fetch the user profile once on client mount. The helper will redirect if needed.
    console.log('Layout onMount: fetching user profile');
    fetchUserProfile().catch((e) => console.warn('Profile fetch failed', e));
  });


  
</script>

<Toaster />
<div class="scheme-only-dark h-screen">
  <TitleBar />
  {@render children()}
</div>
