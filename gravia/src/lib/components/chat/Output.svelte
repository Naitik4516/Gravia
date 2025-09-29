<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import MarkdownRenderer from "$lib/components/MarkdownRenderer.svelte";
  import type { Message } from "$lib/chat/types";
  import { Copy, AlertTriangle, Play } from "@lucide/svelte";
  import { Volume2, Square } from "@lucide/svelte";
  import { toast } from "svelte-sonner";
  import gsap from "gsap";
  import { fade } from "svelte/transition";
  import { readFile } from "@tauri-apps/plugin-fs";
  import MediaModal from "./MediaModal.svelte";
  import { migrateTempFileToScreenshots } from "$lib/utils/fileStorage";

  let {
    messages = [],
    isPreparing = false,
    getMessagePosition,
    getIconComponent,
  }: {
    messages?: Message[];
    isResponding?: boolean; // true while streaming response
    isPreparing?: boolean; // true after send before first chunk
    getMessagePosition: (messages: Message[], index: number) => string;
    getIconComponent: (mime: string) => any;
  } = $props();

  import { chatClient } from "$lib/chat/chatService";
  let inputEl: HTMLElement | null = null;
  let activeTTSIndex = $state<number | null>(null);
  let ttsActive = $state(false);

  let isModalOpen = $state(false);
  let modalSrc = $state("");
  let modalType = $state<"image" | "video" | "audio">("image");

  // Cache for blob URLs to avoid re-reading files
  let blobCache = new Map<string, string>();

  function hasRenderableContent(message: Message): boolean {
    if (!message) return false;
    const hasText = typeof message.content === "string" && message.content.trim().length > 0;
    const hasImages = Array.isArray(message.images) && message.images.length > 0;
    const hasVideos = Array.isArray(message.videos) && message.videos.length > 0;
    const hasAudios = Array.isArray(message.audios) && message.audios.length > 0;
    const hasFiles = Array.isArray(message.files) && message.files.length > 0;
    return hasText || hasImages || hasVideos || hasAudios || hasFiles;
  }

  function findAssistantIndexForContent(content?: string | null): number | null {
    if (!Array.isArray(messages) || messages.length === 0) {
      return null;
    }

    if (typeof content === "string" && content.trim().length > 0) {
      const target = content.trim();
      for (let i = messages.length - 1; i >= 0; i--) {
        const msg = messages[i];
        if (msg.role === "assistant" && msg.content?.trim() === target) {
          return i;
        }
      }
    }

    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") {
        return i;
      }
    }

    return null;
  }

  async function createBlobUrl(filepath: string, mimeType: string): Promise<string> {
    if (blobCache.has(filepath)) {
      return blobCache.get(filepath)!;
    }

    try {
      // First try to migrate temporary file to permanent location if needed
      const migratedPath = await migrateTempFileToScreenshots(filepath);
      const finalPath = migratedPath || filepath;
      
      const fileData = await readFile(finalPath);
      console.log("Read file data:", fileData);
      const blob = new Blob([fileData], { type: mimeType });
      const blobUrl = URL.createObjectURL(blob);
      blobCache.set(filepath, blobUrl);
      return blobUrl;
    } catch (error) {
      console.error("Failed to read file:", filepath, error);
      return "";
    }
  }

  function resolveFilePath(file: { filepath?: string; filePath?: string }): string | undefined {
    return file?.filepath ?? file?.filePath;
  }

  function openModal(src: string, type: "image" | "video" | "audio") {
    modalSrc = src;
    modalType = type;
    isModalOpen = true;
  }

  function closeModal() {
    isModalOpen = false;
  }

  function requestTTS(index: number, text: string) {
    if (!text) return;
    // If already active for this index, send interrupt/stop
    if (ttsActive && activeTTSIndex === index) {
      chatClient.stopSpeaking();
      ttsActive = false;
      activeTTSIndex = null;
      return;
    }
    activeTTSIndex = index;
    ttsActive = true;
    chatClient.speak(text);
  }

  // Subscribe to chatClient events
  onMount(() => {
    const offStart = chatClient.on("tts_start", (text?: string) => {
      ttsActive = true;
      const resolvedIndex = findAssistantIndexForContent(text ?? undefined);
      if (resolvedIndex !== null) {
        activeTTSIndex = resolvedIndex;
      } else if (activeTTSIndex === null) {
        const fallbackIndex = findAssistantIndexForContent();
        if (fallbackIndex !== null) {
          activeTTSIndex = fallbackIndex;
        }
      }
    });
    const offComplete = chatClient.on("tts_complete", () => {
      ttsActive = false;
      activeTTSIndex = null;
    });
    inputEl = document.getElementById("chat-input-container");
    return () => {
      offStart();
      offComplete();
    };
  });

  onMount(() => {
    inputEl = document.getElementById("chat-input-container");
  });

  // Clean up blob URLs on component destroy to prevent memory leaks
  onDestroy(() => {
    for (const blobUrl of blobCache.values()) {
      URL.revokeObjectURL(blobUrl);
    }
    blobCache.clear();
  });

  function handleCopy(content?: string) {
    if (!content) return;
    navigator.clipboard
      ?.writeText(content)
      .then(() => {
        toast.success("Message copied to clipboard");
      })
      .catch(() => {});
  }

  // Rename previous animateIn to animateUser and add animateAI
  function animateUser(node: HTMLElement, active = true) {
    if (!active) return;
    
    // Get input element each time in case it wasn't set during onMount
    const currentInputEl = inputEl || document.getElementById("chat-input-container");
    if (!currentInputEl) {
      // If no input element found, just do a simple fade-in animation
      gsap.from(node, {
        opacity: 0,
        y: 20,
        duration: 0.3,
        ease: "power2.out",
      });
      return;
    }
    
    const inputRect = currentInputEl.getBoundingClientRect();
    const targetRect = node.getBoundingClientRect();
    const dx =
      inputRect.left +
      inputRect.width / 2 -
      (targetRect.left + targetRect.width / 2);
    const dy = inputRect.top - targetRect.top;
    gsap.from(node, {
      opacity: 0,
      y: dy,
      x: dx,
      scale: 0.85,
      duration: 0.4, // Reduced from 0.7 to make it faster
      ease: "power3.out",
    });
  }
  // function animateAI(node: HTMLElement, active = true) {
  //   if (!active) return;
  //   console.log("animating...")
  //   gsap.from(node, { opacity: 0, duration: 1, ease: 'power2.out' });
  // }
</script>

<MediaModal
  src={modalSrc}
  type={modalType}
  isOpen={isModalOpen}
  onClose={closeModal}
/>

{#each messages as message, index (message.id || `${message.timestamp?.getTime()}-${index}`)}
  {@const skipAssistant = message.role === "assistant" && !hasRenderableContent(message)}
  {#if !skipAssistant}
    <div
      class="relative  flex {message.role === 'user'
        ? 'justify-end'
        : 'justify-start'} w-full"
    >
    <div
      class={` group max-w-[85%] px-5 py-2 my-2 font-medium shadow-2xl overflow-hidden rounded-3xl ${
        message.role === "user"
          ? "bg-gradient-to-br from-purple-700 to-indigo-900 text-white shadow-lg rounded-br-xs  my-3 text-right max-w-[60%]"
          : message.role === "error"
            ? "bg-gradient-to-br from-red-600 to-red-800 text-white border border-red-500/30 rounded-bl-xs"
            : "bg-white/5 text-gray-100 tracking-wide rounded-bl-xs  "
      } ${message.role === "assistant" ? (getMessagePosition(messages, index) === "first" ? "rounded-bl-none" : getMessagePosition(messages, index) === "middle" ? "rounded-tl-xs rounded-bl-xs bg-white/7 shadow-none" : getMessagePosition(messages, index) === "last" ? "rounded-tl-none" : "rounded-bl") : ""}`}
    >
      {#if message.content}
        <div class="flex items-start gap-2">
          {#if message.role === "error"}
            <div class="mt-1 flex-shrink-0">
              <AlertTriangle class="w-4 h-4 text-red-800" />
            </div>
          {/if}
          <div class="flex-1 min-w-0 overflow-hidden">
            <MarkdownRenderer
              content={message.content}
              enableMarkdown={message.role !== "error"}
              className=""
            />
          </div>
        </div>
      {/if}

      <div class="mt-2 grid gap-2 {!message.images && !message.videos && !message.audios && !message.files && !message.content ? 'mt-0' : ''}">
        {#if message.images}
          {#each message.images as file}
            {@const filePath = resolveFilePath(file)}
            {#if filePath}
              {#await createBlobUrl(filePath, file.type || "image/jpeg") then src}
                {#if src}
                  <button
                    class="w-fit cursor-pointer"
                    onclick={() => openModal(src, "image")}
                  >
                    <img
                      {src}
                      alt={file.name}
                      class="max-w-xs max-h-40 rounded-3xl"
                    />
                  </button>
                {/if}
              {/await}
            {:else if file.dataUrl}
              <button
                class="w-fit cursor-pointer"
                onclick={() => openModal(file.dataUrl!, "image")}
              >
                <img
                  src={file.dataUrl}
                  alt={file.name}
                  class="max-w-xs max-h-40 rounded-3xl"
                />
              </button>
            {/if}
          {/each}
        {/if}

        {#if message.videos}
          {#each message.videos as file}
            {@const filePath = resolveFilePath(file)}
            {#if filePath}
              {#await createBlobUrl(filePath, file.type || "video/mp4") then src}
                {#if src}
                  <button
                    class="relative w-fit cursor-pointer"
                    onclick={() => openModal(src, "video")}
                  >
                    <video
                      {src}
                      class="max-w-xs max-h-40 rounded-3xl"
                      preload="metadata"
                    >
                      <track kind="captions" label="Captions" />
                    </video>
                    <div
                      class="absolute inset-0 flex items-center justify-center bg-black/40"
                    >
                      <Play class="w-10 h-10 text-white" />
                    </div>
                  </button>
                {/if}
              {/await}
            {:else if file.dataUrl}
              <button
                class="relative w-fit cursor-pointer"
                onclick={() => openModal(file.dataUrl!, "video")}
              >
                <video
                  src={file.dataUrl}
                  class="max-w-xs max-h-40 rounded-3xl"
                  preload="metadata"
                >
                  <track kind="captions" label="Captions" />
                </video>
                <div
                  class="absolute inset-0 flex items-center justify-center bg-black/40"
                >
                  <Play class="w-10 h-10 text-white" />
                </div>
              </button>
            {/if}
          {/each}
        {/if}

        {#if message.audios}
          {#each message.audios as file}
            {@const filePath = resolveFilePath(file)}
            {#if filePath}
              {#await createBlobUrl(filePath, file.type || "audio/mpeg") then src}
                {#if src}
                  <button
                    class="w-fit cursor-pointer"
                    onclick={() => openModal(src, "audio")}
                    aria-label="Open audio in modal"
                  >
                    <audio {src} controls class="w-full max-w-xs"></audio>
                  </button>
                {/if}
              {/await}
            {:else if file.dataUrl}
              <button
                class="w-fit cursor-pointer"
                onclick={() => openModal(file.dataUrl!, "audio")}
                aria-label="Open audio in modal"
              >
                <audio src={file.dataUrl} controls class="w-full max-w-xs"></audio>
              </button>
            {/if}
          {/each}
        {/if}

        {#if message.files}
          {#each message.files as file}
            {@const filePath = resolveFilePath(file)}
            {#if file.type?.startsWith("image/")}
              {#if filePath}
                {#await createBlobUrl(filePath, file.type || "image/jpeg") then src}
                  {#if src}
                    <button
                      class="w-fit cursor-pointer"
                      onclick={() => openModal(src, "image")}
                    >
                      <img
                        {src}
                        alt={file.name}
                        class="max-w-md max-h-46 rounded-3xl"
                      />
                    </button>
                  {/if}
                {/await}
              {:else if file.dataUrl}
                <button
                  class="w-fit cursor-pointer"
                  onclick={() => openModal(file.dataUrl!, "image")}
                >
                  <img
                    src={file.dataUrl}
                    alt={file.name}
                    class="max-w-sm max-h-46 rounded-3xl"
                  />
                </button>
              {/if}
            {:else if file.type?.startsWith("video/")}
              {#if filePath}
                {#await createBlobUrl(filePath, file.type || "video/mp4") then src}
                  {#if src}
                    <button
                      class="relative w-fit cursor-pointer"
                      onclick={() => openModal(src, "video")}
                    >
                      <video
                        {src}
                        class="max-w-xs max-h-40 rounded-3xl"
                        preload="metadata"
                      >
                        <track kind="captions" label="Captions" />
                      </video>
                      <div
                        class="absolute inset-0 flex items-center justify-center bg-black/40"
                      >
                        <Play class="w-10 h-10 text-white" />
                      </div>
                    </button>
                  {/if}
                {/await}
              {:else if file.dataUrl}
                <button
                  class="relative w-fit cursor-pointer"
                  onclick={() => openModal(file.dataUrl!, "video")}
                >
                  <video
                    src={file.dataUrl}
                    class="max-w-xs max-h-40 rounded-3xl"
                    preload="metadata"
                  >
                    <track kind="captions" label="Captions" />
                  </video>
                  <div
                    class="absolute inset-0 flex items-center justify-center bg-black/40"
                  >
                    <Play class="w-10 h-10 text-white" />
                  </div>
                </button>
              {/if}
            {:else if file.type?.startsWith("audio/")}
              {#if filePath}
                {#await createBlobUrl(filePath, file.type || "audio/mpeg") then src}
                  {#if src}
                    <button
                      class="w-fit cursor-pointer"
                      onclick={() => openModal(src, "audio")}
                      aria-label="Open audio in modal"
                    >
                      <audio {src} controls class="w-full max-w-xs"></audio>
                    </button>
                  {/if}
                {/await}
              {:else if file.dataUrl}
                <button
                  class="w-fit cursor-pointer"
                  onclick={() => openModal(file.dataUrl!, "audio")}
                  aria-label="Open audio in modal"
                >
                  <audio src={file.dataUrl} controls class="w-full max-w-xs"></audio>
                </button>
              {/if}
            {:else}
              {@const Icon = getIconComponent(file.type)}
              <div class="flex items-center rounded-2xl bg-black/40 p-3 w-fit max-w-64">
                <div
                  class="w-13 h-11 rounded-xl flex items-center justify-center mr-3 bg-purple-800/80"
                >
                  <Icon class="w-5 h-5 text-gray-300" />
                </div>
                <div class="flex flex-col">
                  <span class="text-sm text-gray-200 font-semibold text-left leading-tight font-['Roboto']"
                    >{file.name}</span
                  >
                  <div class="flex items-center gap-2 mt-1">
                    <span class="text-xs uppercase text-gray-300"
                      >{file.name.split(".").pop()}</span
                    >
                    <span class="text-xs text-gray-400"
                      >{(file as any).size &&
                        ((file as any).size / 1024).toFixed(1)}KB</span
                    >
                  </div>
                </div>
              </div>
            {/if}
          {/each}
        {/if}
      </div>
      {#if message.role === "assistant" && message.content}
        <div
          class="absolute -bottom-3 left-2 w-24 invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-opacity pointer-events-none group-hover:pointer-events-auto bg-slate-900/60 rounded-full z-10"
        >
          <div class="group/btn flex gap-1 justify-evenly">
            <button
              class=" hover:bg-gray-600/40 rounded-full p-2 flex items-center justify-center transition-colors ml-2 cursor-pointer"
              aria-label="Copy message"
              onclick={() => handleCopy(message.content)}
            >
              <Copy class="w-3 h-3" />
            </button>
            <button
              class=" hover:bg-gray-600/40 rounded-full p-2 flex items-center justify-center transition-colors cursor-pointer"
              aria-label={ttsActive && activeTTSIndex === index
                ? "Stop"
                : "Speak"}
              onclick={() => requestTTS(index, message.content)}
            >
              {#if ttsActive && activeTTSIndex === index}
                <Square class="w-3 h-3" />
              {:else}
                <Volume2 class="w-3 h-3" />
              {/if}
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>
  {/if}
{/each}
{#if isPreparing}
  <div class="flex justify-start w-full">
    <div
      class="bg-gray-900 text-gray-100 px-4 py-2 rounded-xl max-w-[80%]"
    >
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  </div>
{/if}

<style>
  .typing-indicator {
    display: flex;
    align-items: center;
    column-gap: 6px;
    padding: 8px 0;
  }
  .typing-indicator span {
    height: 8px;
    width: 8px;
    background-color: #a78bfa;
    border-radius: 50%;
    display: block;
    opacity: 0.4;
  }
  .typing-indicator span:nth-child(1) {
    animation: wave 1s infinite ease-in-out;
  }
  .typing-indicator span:nth-child(2) {
    animation: wave 1s infinite ease-in-out 0.2s;
  }
  .typing-indicator span:nth-child(3) {
    animation: wave 1s infinite ease-in-out 0.4s;
  }
  @keyframes wave {
    0%, 60%, 100% {
      transform: translateY(0) scale(1);
      opacity: 0.4;
    }
    30% {
      transform: translateY(-10px) scale(1.2);
      opacity: 1;
    }
  }
  @keyframes fadeOut {
    0% {
      opacity: 0;
      transform: translate(-50%, 4px);
    }
    10% {
      opacity: 1;
      transform: translate(-50%, 0);
    }
    90% {
      opacity: 1;
    }
    100% {
      opacity: 0;
    }
  }

  /* Ensure proper text handling in message containers */
  .group {
    word-wrap: break-word;
    overflow-wrap: break-word;
    min-width: 0;
  }
  
  /* Improve code block display within messages */
  :global(.group :is(pre, code)) {
    max-width: 100%;
    overflow-x: auto;
  }
</style>