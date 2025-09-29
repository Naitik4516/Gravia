<script lang="ts">
  import type { Snippet } from "svelte";
  import { onMount } from "svelte";
  import { gsap } from "gsap";
  
  let { children }: { children: Snippet } = $props();

  let mainCard: HTMLDivElement;
  let bgBlur1: HTMLDivElement;
  let bgBlur2: HTMLDivElement;
  let innerBlur1: HTMLDivElement;
  let innerBlur2: HTMLDivElement;

  onMount(() => {
    // Set initial states
    gsap.set([bgBlur1, bgBlur2, innerBlur1, innerBlur2], { 
      scale: 0, 
      opacity: 0 
    });
    gsap.set(mainCard, { 
      scale: 1.2, 
      opacity: 0 
    });

    // Create timeline for entrance animations
    const tl = gsap.timeline();
    
    // Animate main container first with zoom-out effect
    tl.to(mainCard, {
      scale: 1,
      opacity: 0.9,
      duration: 0.9,
      ease: "back.out(1.7)"
    })

    // Then animate all blur elements in parallel
    .to([bgBlur1, bgBlur2, innerBlur1, innerBlur2], {
      scale: 1,
      opacity: (i) => i < 2 ? 0.7 : 0.4, // First two get 0.7, last two get 0.4
      duration: 1,
      ease: "expo.out",
      stagger: 0.1
    }, "-=0.3");
  });
</script>

<div  class="w-screen h-screen relative bg-gray-950 overflow-hidden flex items-center justify-center ">
  <div bind:this={bgBlur1} class="size-64 left-10 -top-12 absolute opacity-70 bg-violet-800 rounded-full blur-[120px]"></div>
  <div bind:this={bgBlur2} class="size-64 -right-7 -bottom-14 absolute opacity-70 bg-purple-600 rounded-full blur-[120px]"></div>
  <div bind:this={mainCard} class=" flex flex-col justify-center items-center md:px-16 w-4/5 h-4/5 absolute opacity-90 bg-indigo-300/5 rounded-md outline-1 outline-white/20 backdrop-blur-[55px] overflow-hidden">
      {@render children()}
    <div bind:this={innerBlur1} class="size-40 -left-6 -bottom-14 absolute opacity-40 bg-teal-300 rounded-full blur-[100px]"></div>
    <div bind:this={innerBlur2} class="size-40 right-16 top-4 absolute opacity-60 bg-[#ED409F] rounded-full blur-[100px]"></div>
  </div>
</div>