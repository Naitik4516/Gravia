<script lang="ts">
  import type { HTMLInputAttributes } from "svelte/elements";
  import { Mail, Lock, User } from "@lucide/svelte";

  interface Props extends HTMLInputAttributes {
    label: string;
    value?: string | number | null | undefined;
    iconName?: "email" | "password" | "user";
  }

  let { label, iconName, value = $bindable(), ...restProps }: Props = $props();
  let id = `auth-input-${Math.random().toString(36).substring(2, 9)}`;

  let isFocused = $state(false);
  let hasValue = $derived(value && value.toString().length > 0);
  let labelActive = $derived(isFocused || hasValue);

  const icons = {
    email: Mail,
    password: Lock,
    user: User,
  };

  let currentIcon = $derived(iconName && icons[iconName]);

  function handleFocus() {
    isFocused = true;
  }

  function handleBlur() {
    isFocused = false;
  }
</script>

<div class="relative mb-4 w-full">
  {#if currentIcon}
    <span
      class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none z-10"
    >
      <svelte:component this={currentIcon} size={20} />
    </span>
  {/if}

  <input
    {...restProps}
    {id}
    class="w-full py-4 px-1 {currentIcon
      ? 'pl-12'
      : 'pl-4'} pr-4 bg-black/20 border border-white/10 rounded-lg text-gray-200 text-sm outline-none transition-all duration-200 focus:border-purple-500 focus:shadow-[0_0_0_3px_rgba(142,45,226,0.3)]"
    bind:value
    onfocus={handleFocus}
    onblur={handleBlur}
  />

  <label
    for={id}
    class="absolute pointer-events-none transition-all duration-200 ease-in-out origin-left px-0.5
           {labelActive
      ? 'top-0 -translate-y-1/2 text-xs text-purple-400 bg-slate-950'
      : 'top-1/2 -translate-y-1/2 text-sm text-gray-400'}
           {currentIcon && !labelActive
      ? 'left-11'
      : labelActive
        ? 'left-3'
        : currentIcon
          ? 'left-11'
          : 'left-3'}"
  >
    {label}
  </label>
</div>
