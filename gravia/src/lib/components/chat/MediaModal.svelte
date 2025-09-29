<script lang="ts">
  import { X } from "@lucide/svelte";

  let {
    src,
    type,
    isOpen,
    onClose,
  }: {
    src: string;
    type: "image" | "video" | "audio";
    isOpen: boolean;
    onClose: () => void;
  } = $props();

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      onClose();
    }
  }

  function handleBackdropKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClose();
    }
  }

  function handleContentKeydown(event: KeyboardEvent) {
    // Stop propagation to prevent backdrop from closing
    event.stopPropagation();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 "
    role="button"
    tabindex="0"
    onclick={onClose}
    onkeydown={handleBackdropKeydown}
  >
    <div
      class="relative max-w-4xl max-h-[90vh] rounded-lg"
      role="dialog"
      tabindex="0"
      onclick={(e) => e.stopPropagation()}
      onkeydown={handleContentKeydown}
    >
      {#if type === "image"}
        <img {src} alt="Preview" class="object-contain w-full h-full rounded-lg" />
      {:else if type === "video"}
        <video {src} controls autoplay class="object-contain w-full h-full rounded-lg">
          <track kind="captions" />
        </video>
      {:else if type === "audio"}
        <audio {src} controls autoplay class="w-full">
          <track kind="captions" />
        </audio>
      {/if}
      <button
        class="absolute top-4 right-4 text-white hover:text-gray-300 cursor-pointer"
        onclick={onClose}
      >
        <X class="w-8 h-8" />
      </button>
    </div>
  </div>
{/if}