<script lang="ts">
  import { page } from "$app/state";
  import { categories } from "$lib/settings";

  let activeSection = $derived(page.url.pathname.split("/").pop() || "");
</script>

<nav
  class="h-[calc(100vh-2rem)] w-72 py-10 rounded-xl bg-white/10 font-['Orbitron'] shadow-[0px_4px_30px_0px_rgba(64,55,81,0.25)] backdrop-blur-lg"
>
  <h2 class="font-black text-4xl text-center mb-10">Settings</h2>
  <div
    class="left-6 -top-14 absolute size-56 bg-[#05D9FF]/50 rounded-full blur-[152px] pointer-events-none"
  ></div>
  <div
    class="left-6 bottom-12 absolute size-56 bg-[#C5FF05]/50 rounded-full blur-[152px] pointer-events-none"
  ></div>

  <ul class="overflow-y-auto max-h-[90%] w-full inset-shadow-sm " >
    {#each Object.entries(categories) as [key, label]}
      <li
        class="mx-4 transition-colors rounded-lg hover:bg-white/5 shadow-lg hover:shadow-xl {activeSection ===
        key
          ? 'bg-white/10'
          : ''}"
      >
        <a
          class="flex items-center gap-2 p-4 text-lg font-semibold text-white bg-white/5 rounded-lg"
          href={`/settings/${key}`}>{label}</a
        >
      </li>
    {/each}
  </ul>
</nav>

<style>
  li {
    padding: 0;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
</style>
