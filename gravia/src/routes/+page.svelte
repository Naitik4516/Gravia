<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import {
      chatClient,
      classifyQueryWithScreenshot,
      createErrorMessage,
      createUserMessage,
      getMessagePosition,
  } from "$lib/chat/chatService";
  import type { ClassifyResult } from "$lib/chat/chatService";
  import type { Message } from "$lib/chat/types";
  import { getIconComponent } from "$lib/chat/uiStateService";
  import ArtifactCard from "$lib/components/chat/ArtifactCard.svelte";
  import Input from "$lib/components/chat/Input.svelte";
  import Output from "$lib/components/chat/Output.svelte";
  import StatusDisplay from "$lib/components/chat/StatusDisplay.svelte";
  import { sseService } from '$lib/sseService';
  import { globalState } from "$lib/state.svelte";
  import { conversationSettings } from '$lib/stores/conversation';
  import { saveScreenshotBase64 } from "$lib/utils/fileStorage";
  import { onMount, tick } from "svelte";
  import { invoke } from '@tauri-apps/api/core';
  import type { PageProps } from "./$types";


  let { data }: PageProps = $props();

  let messages = $state<Message[]>(data?.messages || []);
  let artifacts = $state<{ name: string; path: string; data_b64?: string; }[]>([]);
  let isResponding = $state(false);
  let isPreparing = $state(false);
  let isScrolledUp = $state(false);
  let autoCaptureScreen = $state(true);

  let chatContainer: HTMLElement;

  function parseDataUrl(dataUrl: string): { mime: string; base64: string } | null {
    if (!dataUrl?.startsWith("data:")) return null;
    const match = dataUrl.match(/^data:(.+?);base64,(.*)$/);
    if (!match) return null;
    return { mime: match[1], base64: match[2] };
  }

  function getExtensionFromMime(mime: string): string {
    const map: Record<string, string> = {
      "image/png": "png",
      "image/jpeg": "jpg",
      "image/jpg": "jpg",
      "image/webp": "webp",
      "image/gif": "gif",
      "image/svg+xml": "svg",
      "image/bmp": "bmp",
      "image/tiff": "tiff",
    };
    if (map[mime]) return map[mime];
    const fallback = mime.split("/")[1];
    return fallback ? fallback.split(";")[0] : "png";
  }

  function messageHasRenderableContent(message?: Message | null): boolean {
    if (!message) return false;
    const hasText = typeof message.content === "string" && message.content.trim().length > 0;
    const hasImages = Array.isArray(message.images) && message.images.length > 0;
    const hasVideos = Array.isArray(message.videos) && message.videos.length > 0;
    const hasAudios = Array.isArray(message.audios) && message.audios.length > 0;
    const hasFiles = Array.isArray(message.files) && message.files.length > 0;
    return hasText || hasImages || hasVideos || hasAudios || hasFiles;
  }

  
  // profile fetching is handled centrally in +layout.svelte using src/lib/auth.ts
  onMount(() => {
    conversationSettings.fetch();
  });


  // Reactive effect to handle new chat requests
  $effect(() => {
    if (page.url.searchParams.has('newchat')) {
      // Reset messages and artifacts when new chat is initiated
      messages = [];
      artifacts = [];
      isResponding = false;
      isPreparing = false;
      isScrolledUp = false;
      
      // Clean up the URL by removing the newchat parameter
      const newUrl = new URL(page.url);
      newUrl.searchParams.delete('newchat');
      const cleanPath = newUrl.pathname + (newUrl.search || '');
      goto(cleanPath, { replaceState: true });
    }
  });

  function scrollToBottom() {
    if (chatContainer) {
      requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      });
    }
  }

  function handleScroll() {
    if (!chatContainer) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainer;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
    isScrolledUp = !isAtBottom;
  }

  $effect.pre(() => {
    if (!chatContainer) return; // not yet mounted

    // reference `messages` array length so that this code re-runs whenever it changes
    messages.length;

    // autoscroll when new messages are added
    if (
      chatContainer.offsetHeight + chatContainer.scrollTop >
      chatContainer.scrollHeight - 20
    ) {
      tick().then(() => {
        chatContainer.scrollTo(0, chatContainer.scrollHeight);
      });
    }
  });

  let currentStreamingIndex: number | null = null;

  onMount(() => {
    // setup chat client listeners
    chatClient.connect();
    sseService.start();
    chatClient.on("start", () => {
      // create placeholder assistant message for streaming
      const assistantMsg = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
      } as Message;
      messages = [...messages, assistantMsg];
      currentStreamingIndex = messages.length - 1;
      isResponding = true; // currently streaming (or will stream soon)
      isPreparing = true; // show pre-stream typing indicator
      isScrolledUp = false;
    });
    chatClient.on("chunk", (data) => {
      if (isPreparing) isPreparing = false; // first chunk received
      if (currentStreamingIndex != null && messages[currentStreamingIndex]) {
        const chunkContent = data.message;
        if (chunkContent) { // Only process non-empty chunks
          messages[currentStreamingIndex] = {
            ...messages[currentStreamingIndex],
            content: messages[currentStreamingIndex].content + chunkContent,
            timestamp: new Date(),
          };
          // trigger reactive update
          messages = [...messages];
        }
      }
    });
    chatClient.on("end", () => {
      const streamingIndex = currentStreamingIndex;
      isResponding = false;
      isPreparing = false;
      if (streamingIndex != null && messages[streamingIndex]) {
        const candidate = messages[streamingIndex];
        if (!messageHasRenderableContent(candidate)) {
          messages = messages.filter((_, idx) => idx !== streamingIndex);
        } else {
          messages = [...messages];
        }
      }
      currentStreamingIndex = null;
    });
    chatClient.on("error", (err) => {
      // Create an error message to display in the chat
      const errorMessage = createErrorMessage(
        `Connection Error: ${err?.message || err || "Unknown error occurred"}`,
      );
      messages = [...messages, errorMessage];

      // If there was a streaming message, clean it up
      if (currentStreamingIndex != null && messages[currentStreamingIndex]) {
        messages[currentStreamingIndex] = {
          ...messages[currentStreamingIndex],
          content:
            messages[currentStreamingIndex].content + `\n\n*Error:* ${err}`,
        };
      }

      isResponding = false;
      isPreparing = false;
    });
    chatClient.on("new_chat", () => {
      // Reset UI state when new chat is initiated
      messages = [];
      artifacts = [];
      isResponding = false;
      isPreparing = false;
      isScrolledUp = false;
      currentStreamingIndex = null;
    });
    
    // Handle file artifacts
    chatClient.on("file_artifact", (artifact) => {
      // Avoid duplicates by checking if artifact already exists
      const exists = artifacts.some(a => a.path === artifact.path);
      if (!exists) {
        artifacts = [...artifacts, artifact];
      }
    });

    chatClient.on("image", async (imagePayload) => {
      if (!imagePayload?.data || typeof imagePayload.data !== "string") return;
      const parsed = parseDataUrl(imagePayload.data);
      if (!parsed) return;

      const mime = imagePayload.mime || parsed.mime || "image/png";
      const extension = getExtensionFromMime(mime);
      const fileName = imagePayload.name || `generated-image-${Date.now()}.${extension}`;

      let filePath: string | undefined;
      try {
        filePath = await saveScreenshotBase64(parsed.base64, fileName);
      } catch (error) {
        console.error("Failed to persist generated image", error);
      }

      const mediaEntry = {
        name: fileName,
        type: mime,
        filepath: filePath,
        filePath,
        dataUrl: imagePayload.data,
      };

      if (currentStreamingIndex != null && messages[currentStreamingIndex]) {
        const current = messages[currentStreamingIndex];
        const updatedImages = current.images ? [...current.images, mediaEntry] : [mediaEntry];
        messages[currentStreamingIndex] = {
          ...current,
          images: updatedImages,
          timestamp: new Date(),
        };
      } else {
        const newMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "",
          timestamp: new Date(),
          images: [mediaEntry],
        };
        messages = [...messages, newMessage];
        currentStreamingIndex = messages.length - 1;
      }

      messages = [...messages];
      tick().then(() => scrollToBottom());
    });
    
    // Handle TTS events for proper propagation to components
    chatClient.on("tts_start", (data) => {
      // TTS events are handled by Output.svelte component directly
      console.log("TTS started:", data);
    });
    
    chatClient.on("tts_complete", (data) => {
      // TTS events are handled by Output.svelte component directly  
      console.log("TTS completed:", data);
    });
  });

  conversationSettings.subscribe(settings => {
    if (settings && typeof settings.auto_capture_screen === 'boolean') {
      autoCaptureScreen = settings.auto_capture_screen;
    }
  });

  async function handleSend(payload: {
    text: string;
    files: any[];
    agent?: string;
  }) {
    const { text, files, agent } = payload;
    let screenshotDataUrl: string | null = null;
    // if (autoCaptureScreen && (!files || files.length === 0)) {
    //   let classification: ClassifyResult | null = null; 
    //   try {
    //     console.log('[AutoCapture] invoking classifier with', messages.slice(-2).map(m=>m.role+':'+m.content.slice(0,30)));
    //     classification = await classifyQueryWithScreenshot(messages, text, true);
    //     console.log('[AutoCapture] classifier result', classification);
    //     if (classification?.classification?.needs_screenshot && classification?.screenshot_base64) {
    //       screenshotDataUrl = `data:image/png;base64,${classification.screenshot_base64}`;
    //     } else if (classification && classification.classification?.needs_screenshot && !classification.screenshot_base64) {
    //       console.warn('[AutoCapture] classifier requested screenshot but none returned');
    //     }
    //   } catch (e) {
    //     console.warn('[AutoCapture] classifier flow failed, attempting direct capture fallback', e);
    //   }
    //   if (!screenshotDataUrl && classification && classification.classification?.needs_screenshot) {
    //     try {
    //       const directNeeded = await invoke<string>('capture_screenshot_base64');
    //       if (directNeeded) {
    //         screenshotDataUrl = `data:image/png;base64,${directNeeded}`;
    //         console.log('[AutoCapture] fallback capture succeeded after missing screenshot payload');
    //       }
    //     } catch (inner) {
    //       console.warn('[AutoCapture] fallback capture (needed) failed', inner);
    //     }
    //   }
    // }
     const userMessage = createUserMessage(
      text,
      files?.length ? files : undefined,
    );
    if (screenshotDataUrl) {
      // Attach screenshot as a pseudo file and save to persistent location
      const base64Data = screenshotDataUrl.split(',')[1];
      const persistentPath = await saveScreenshotBase64(base64Data, `screenshot-${Date.now()}.png`);
      
      const screenshotAttachment = {
        id: crypto.randomUUID(),
        name: `screenshot-${Date.now()}.png`,
        type: 'image/png',
        size: screenshotDataUrl.length * 0.75,
        filePath: persistentPath,
        dataUrl: screenshotDataUrl
      };
      userMessage.files = userMessage.files ? [...userMessage.files, screenshotAttachment] : [screenshotAttachment];
    }
     
     // Add user message and ensure UI updates
     messages = [...messages, userMessage];
     isScrolledUp = false;
     
     // Force a UI update cycle before sending to server
     await tick();
     scrollToBottom();
     
     // send to server
     chatClient.sendMessage(text, userMessage.files, agent || "general");
   }
</script>

<div
  class="flex flex-col h-screen selection:bg-purple-500 selection:text-white overflow-hidden m-0"
>
  <div class="flex flex-col relative h-full">
    {#if messages.length === 0}
      <div class="flex flex-1 items-center justify-center">
        <h1
          class="text-3xl md:text-4xl font-semibold text-center text-gray-200 mb-2 px-4 my-auto"
        >
          <!-- Hi There! How can I help you? -->
          Hi {globalState.user?.name?.split(" ")[0] || "There"}! How can I help you?
        </h1>
      </div>
    {/if}
    <div
      bind:this={chatContainer}
      class="flex-1 flex flex-col overflow-y-auto w-full scroll-smooth "
      onscroll={handleScroll}
    >
      <div class="w-full xl:max-w-6xl max-w-5xl mx-auto px-5 pt-14 pb-34">
        <Output
          {messages}
          {isPreparing}
          {getMessagePosition}
          {getIconComponent}
        />
        
        <!-- Artifacts Section -->
        {#if artifacts.length > 0}
          <div class="mt-6 space-y-3">
            <h3 class="text-sm font-medium text-gray-400 px-2">Generated Files</h3>
            {#each artifacts as artifact (artifact.path)}
              <ArtifactCard {artifact} />
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Floating Input component -->
    <Input {isScrolledUp} {isResponding} send={handleSend} />
    <StatusDisplay />
  </div>
</div>

<style>
  :global(.shadow-glow) {
    box-shadow:
      0 0 20px rgba(168, 85, 247, 0.6),
      0 0 40px rgba(168, 85, 247, 0.4),
      0 0 60px rgba(168, 85, 247, 0.2),
      0 10px 30px rgba(0, 0, 0, 0.5);
  }
  :global(.shadow-glow-subtle) {
    box-shadow:
      0 0 15px rgba(168, 85, 247, 0.4),
      0 0 25px rgba(168, 85, 247, 0.2),
      0 5px 20px rgba(0, 0, 0, 0.3);
  }
  @keyframes pulse-subtle {
    0%,
    100% {
      opacity: 1;
      box-shadow:
        0 0 15px rgba(168, 85, 247, 0.5),
        0 0 30px rgba(168, 85, 247, 0.3);
    }
    50% {
      opacity: 0.9;
      box-shadow:
        0 0 20px rgba(168, 85, 247, 0.6),
        0 0 40px rgba(168, 85, 247, 0.4),
        0 0 60px rgba(168, 85, 247, 0.2);
    }
  }
  :global(.animate-pulse-subtle) {
    animation: pulse-subtle 10s infinite ease-in-out;
  }
</style>
