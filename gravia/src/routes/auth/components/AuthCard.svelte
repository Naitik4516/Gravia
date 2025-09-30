<script lang="ts">
  import SkewedButton from "$lib/components/ui/button/SkewedButton.svelte";

  let { title, subtitle="", children, primaryButton="", onsubmit, submitting=false } = $props();
</script>

<form method="POST" class="flex flex-col items-center justify-between w-full h-full py-10" onsubmit={onsubmit}>
  <div class="flex flex-col items-center justify-center mb-5">
    <h1 class="font-black md:text-6xl text-5xl mb-2 ">{title}</h1>
    <p class="text-center text-white font-['Rubik'] leading-tight w-4/5 lg:text-lg text-base">
      {subtitle}
    </p>
  </div>
  <div class="lg:w-1/2 w-4/5  h-full flex flex-col justify-center align-middle" >
    {@render children()}
  </div>
  <div class="flex flex-row justify-end w-full mt-10 px-8">
    {#if primaryButton}
      <SkewedButton text={primaryButton} {submitting} />
    {/if}
  </div>
</form>
