<script lang="ts">
  import {
    ChevronUp,
    ChevronDown,
    SquarePen,
    History,
    NotepadTextDashed,
    Settings,
    Library,
    UserRoundPen
  } from "@lucide/svelte";
  import { Home } from "@lucide/svelte";
  import gsap from "gsap";
  import { flip } from "svelte/animate";
  import { chatClient } from "$lib/chat/chatService";
  import { goto } from '$app/navigation';
  import { page } from "$app/state";

  let isMenuOpen = $state(false);

  const menuItems = [
    {
      icon: SquarePen,
      label: "New Chat",
      onclick: () => {
        chatClient.newChat();
        goto('/?newchat');
      },
    },
    {
      icon: History,
      label: "History",
      href: "/history",
    },
    {
      icon: NotepadTextDashed,
      label: "Memory",
      href: "/memory",
    },
    {
      icon: Settings,
      label: "Settings",
      href: "/settings",
    },
    {
      icon: Library,
      label: "Knowledge",
      href: "/knowledge",
    },
    {
      icon: UserRoundPen,
      label: "Profile",
      href: "/profile",
    },
  ];

  const homeItem = { icon: Home, label: "Home", href: "/" };
  const displayedMenuItems = $derived(page.url.pathname !== '/' ? [homeItem, ...menuItems] : menuItems); 

  function handleItemClick(item: (typeof menuItems)[number] | typeof homeItem) {
    console.log("Clicked menu item:", item);
    isMenuOpen = false;
    if ("onclick" in item && typeof item.onclick === "function") {
      item.onclick();
      return;
    } else if ("href" in item && item.href) {
      goto(item.href);
    }
  }

  function toggleMenu() {
    isMenuOpen = !isMenuOpen;
  }

  $effect(() => {
    if (isMenuOpen) {
      gsap.to(".menu", { height: "auto", opacity: 1, duration: 0.5 });
    } else {
      gsap.to(".menu", { height: 0, opacity: 0, duration: 0.5 });
    }
  });
</script>

<span class="relative flex flex-col items-center gap-2 z-20">
  <div
    onmouseleave={toggleMenu}
    role="menu"
    tabindex="0"
    class={isMenuOpen
      ? "rounded-full bg-white/5 backdrop-blur-xl ring-1 ring-white/10 shadow-xl px-2 pb-4 pt-1  transition-all duration-500 ease-out w-15"
      : ""}
  >
    <button
      onclick={toggleMenu}
      onmouseenter={() => !isMenuOpen && (isMenuOpen = true)}
      class="w-12 h-12 rounded-full flex items-center justify-center
                 {!isMenuOpen
        ? 'hover:bg-white/20 backdrop-blur-md ring-1 ring-white/30 bg-stone-600/20'
        : 'bg-transparent'}
             text-slate-200 hover:text-white focus:outline-none shadow-lg
             transition-all duration-300 ease-out mb-2"
      aria-label="Toggle Menu"
    >
      {#if isMenuOpen}
        <ChevronUp size={20} />
      {:else}
        <ChevronDown size={20} />
      {/if}
    </button>
    <div
      class="menu flex flex-col gap-3 {isMenuOpen
        ? 'h-auto opacity-100 translate-y-0'
        : 'h-0 opacity-0 -translate-y-4 pointer-events-none'}"
    >
      {#each displayedMenuItems as item, index (item)}
        <!-- Single expanding button (icon + label) -->
        <button
          animate:flip
          onclick={() => handleItemClick(item)}
          class={`group flex items-center w-11 h-11 hover:w-32 focus:w-48
                     transition-all duration-400 ease-out overflow-hidden
                     rounded-full bg-white/5 hover:bg-stone-800/50 focus:bg-white/10
                     backdrop-blur-md ring-1 ring-white/10 hover:ring-white/20 focus:ring-white/30
                     text-slate-200 hover:text-white focus:outline-none`}
          aria-label={item.label}
        >
          <div class="flex w-11 justify-center items-center shrink-0">
            <item.icon size={18} class="drop-shadow" />
          </div>
          <span
            class="pr-4 pl-0 opacity-0 translate-x-2
                     group-hover:opacity-100 group-hover:translate-x-0
                     group-focus:opacity-100 group-focus:translate-x-0
                     transition-all duration-300 whitespace-nowrap text-sm font-medium tracking-wide"
          >
            {item.label}
          </span>
        </button>
      {/each}
    </div>

    <!-- Ambient glow -->
    <div
      class="absolute inset-0 -z-10 rounded-2xl bg-gradient-to-b from-sky-400/20 via-indigo-400/10 to-fuchsia-400/20 blur-xl opacity-70"
    ></div>
  </div>
</span>
