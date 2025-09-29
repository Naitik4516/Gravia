<script lang="ts">
  import {
    Paperclip,
    Mic,
    Send,
    X,
    Lightbulb,
    Images,
    Plus
  } from "@lucide/svelte";
  import Button from "$lib/components/ui/button/button.svelte";
  import { fly } from "svelte/transition";
  import type { FileAttachment } from "$lib/chat/types";
  import {
    MAX_ATTACHMENTS_COUNT,
    formatFileSize,
    processFilesForAttachment,
  } from "$lib/chat/attachmentService";
  import {
    determineInputExpansion,
    updateTextareaHeight,
    resetTextareaHeight,
    trimTrailingSpace,
    getIconComponent,
  } from "$lib/chat/uiStateService";
  import { open } from "@tauri-apps/plugin-dialog";
  import { getCurrentWebview } from "@tauri-apps/api/webview";
  import { stat, readFile } from "@tauri-apps/plugin-fs";
  import { gsap } from "gsap";
  import { chatClient } from "$lib/chat/chatService";
  import { invoke } from '@tauri-apps/api/core';
  import { conversationSettings } from '$lib/stores/conversation';
  import { saveScreenshotBase64 } from "$lib/utils/fileStorage";

  const { isScrolledUp = false, send, isResponding = false } = $props();

  let userInput = $state("");
  let isDraggingOver = $state(false);
  let isInputExpanded = $state(false);
  let selectedFiles = $state<FileAttachment[]>([]);
  let showAgentSelector = $state(false);
  let selectedAgentIndex = $state(0);
  let cursorPosition = $state(0);
  let thumbnailErrors = $state<Set<string>>(new Set());
  let previewUrls = $state<Record<string, string>>({});
  const objectUrlMap = new Map<string, string>();
  let isListening = $state(false);
  let transcriptionText = $state("");

  $effect(() => {
    const messageInput = document.getElementById("messageInput") as HTMLTextAreaElement;
    if (messageInput) {
      const newHeight = updateTextareaHeight(messageInput);
      isInputExpanded = determineInputExpansion(newHeight, userInput, selectedFiles.length > 0);
    }
  });

  type AgentKey = "reasoning" | "image";
  let selectedAgent = $state<AgentKey | undefined>();

  // Agent selection via slash commands only
  const agents = [
    {
      name: "/Thinking Agent",
      displayName: "Thinking Agent",
      icon: Lightbulb,
      agent: "reasoning" as AgentKey,
    },
    {
      name: "/Image Agent",
      displayName: "Image Agent",
      icon: Images,
      agent: "image" as AgentKey,
    },
  ];

  let filteredAgents = $state<typeof agents>([]);

  const commandRegex = new RegExp(
    `(${agents.map((c) => c.name).join("|")})\\b`,
    "g",
  );

  function generateHighlightedInput(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(commandRegex, `<span class="text-cyan-400">$1</span>`)
      .replace(/\n/g, "<br />");
  }

  let highlightedInput = $derived(generateHighlightedInput(userInput));

  // Open Tauri file dialog
  async function openFileDialog(): Promise<void> {
    try {
      const selected = await open({
        multiple: true,
        filters: [
          {
            name: "All Files",
            extensions: ["*"],
          },
          {
            name: "Images",
            extensions: ["png", "jpg", "jpeg", "gif", "svg", "webp"],
          },
          {
            name: "Videos",
            extensions: ["mp4", "mov", "avi", "mkv", "webm"],
          },
          {
            name: "Documents",
            extensions: ["pdf", "txt", "md", "json", "csv", "docx", "xlsx"],
          },
          {
            name: "Audio",
            extensions: ["mp3", "wav", "ogg", "m4a", "flac"],
          },
          {
            name: "Source Code",
            extensions: [
              "js",
              "ts",
              "py",
              "java",
              "c",
              "cpp",
              "html",
              "css",
              "rs",
              "go",
              "svelte",
              "jsx",
              "tsx",
            ],
          },
        ],
      });

      if (selected && Array.isArray(selected)) {
        await processFilePaths(selected);
      } else if (selected) {
        await processFilePaths([selected]);
      }
    } catch (error) {
      console.error("Error opening file dialog:", error);
    }
  }

  // Process file paths from Tauri (instead of File objects)
  async function processFilePaths(paths: string[]): Promise<void> {
    if (!paths || paths.length === 0) return;

    try {
      const newAttachments: FileAttachment[] = [];

      for (const path of paths) {
        const fileName = path.split(/[/\\]/).pop() || "unknown";

        // Get file extension to determine MIME type
        const ext = fileName.split(".").pop()?.toLowerCase() || "";
        const mimeType = getMimeTypeFromExtension(ext);

        // Get file metadata using Tauri FS plugin
        let fileSize = 0;
        try {
          const metadata = await stat(path);
          fileSize = metadata.size;
        } catch (statError) {
          console.warn("Could not get file size for:", path, statError);
        }

        // Generate thumbnail for images and videos
        let dataUrl: string | undefined;
        if (mimeType.startsWith("image/") || mimeType.startsWith("video/") || mimeType.startsWith("audio/")) {
          try {
            console.log("Reading file as data URL:", fileName);
            const fileData = await readFile(path);
            const blob = new Blob([fileData], { type: mimeType });
            dataUrl = URL.createObjectURL(blob);
            console.log("Successfully created object URL for:", fileName);
          } catch (readError) {
            console.error("Could not read file to generate data URL:", path, readError);
          }
        }

        // Create FileAttachment with actual file size and thumbnail
        const attachment: FileAttachment = {
          id: crypto.randomUUID(),
          name: fileName,
          type: mimeType,
          size: fileSize,
          filePath: path,
          dataUrl,
        };

        newAttachments.push(attachment);
      }

      if (newAttachments.length > 0) {
        selectedFiles = [...selectedFiles, ...newAttachments];
        isInputExpanded = true;
        queueMicrotask(focusAndResizeTextarea);
      }
    } catch (error) {
      console.error("Error processing file paths:", error);
      alert("Error processing selected files");
    }
  }

  function registerPreview(id: string, url: string) {
    previewUrls = { ...previewUrls, [id]: url };
    if (url.startsWith("blob:")) {
      objectUrlMap.set(id, url);
    }
  }

  function removePreview(id: string) {
    if (objectUrlMap.has(id)) {
      try {
        URL.revokeObjectURL(objectUrlMap.get(id)!);
      } catch (error) {
        console.warn("Failed to revoke object URL", error);
      }
      objectUrlMap.delete(id);
    }
    if (previewUrls[id]) {
      const { [id]: _removed, ...rest } = previewUrls;
      previewUrls = rest;
    }
  }

  async function ensurePreview(file: FileAttachment) {
    if (!file || previewUrls[file.id] || thumbnailErrors.has(file.id)) return;

    if (file.dataUrl) {
      registerPreview(file.id, file.dataUrl);
      return;
    }

    const path = file.filePath ?? (file as any)?.filepath;
    if (!path) return;

    try {
      const fileData = await readFile(path);
      const blob = new Blob([fileData], { type: file.type || "application/octet-stream" });
      const objectUrl = URL.createObjectURL(blob);
      registerPreview(file.id, objectUrl);
    } catch (error) {
      console.error("Failed to load preview for attachment", file.name, error);
      thumbnailErrors.add(file.id);
      thumbnailErrors = new Set(thumbnailErrors);
    }
  }

  // Helper to get MIME type from file extension
  function getMimeTypeFromExtension(ext: string): string {
    const mimeTypes: Record<string, string> = {
      png: "image/png",
      jpg: "image/jpeg",
      jpeg: "image/jpeg",
      gif: "image/gif",
      svg: "image/svg+xml",
      webp: "image/webp",
      pdf: "application/pdf",
      txt: "text/plain",
      md: "text/markdown",
      json: "application/json",
      csv: "text/csv",
      mp4: "video/mp4",
      mov: "video/quicktime",
      avi: "video/x-msvideo",
      mkv: "video/x-matroska",
      webm: "video/webm",
    };
    return mimeTypes[ext] || "application/octet-stream";
  }

  // Process files for attachment
  async function processFiles(files: FileList | File[]): Promise<void> {
    if (!files || files.length === 0) return;
    const filesToProcess = Array.from(files);
    const currentTotalSize = selectedFiles.reduce((sum, f) => sum + f.size, 0);

    const { newAttachments, errors } = await processFilesForAttachment(
      filesToProcess,
      selectedFiles,
      currentTotalSize,
    );

    if (errors.length > 0) alert(errors.join("\n"));

    if (newAttachments.length > 0) {
      selectedFiles = [...selectedFiles, ...newAttachments];
      isInputExpanded = true;
      queueMicrotask(focusAndResizeTextarea);
    }
  }

  $effect(() => {
    selectedFiles.map((file) => file.id);
    for (const file of selectedFiles) {
      ensurePreview(file);
    }
  });

  function focusAndResizeTextarea() {
    const messageInput = document.getElementById(
      "messageInput",
    ) as HTMLTextAreaElement;
    if (messageInput) {
      const newHeight = updateTextareaHeight(messageInput);
      isInputExpanded = determineInputExpansion(
        newHeight,
        userInput,
        selectedFiles.length > 0,
      );
      messageInput.focus();
    }
  }

  function removeSelectedFile(id: string) {
    removePreview(id);
    selectedFiles = selectedFiles.filter((f) => f.id !== id);
    thumbnailErrors.delete(id);
    thumbnailErrors = new Set(thumbnailErrors); // Trigger reactivity
    const messageInput = document.getElementById(
      "messageInput",
    ) as HTMLTextAreaElement;
    if (messageInput) {
      const h = parseFloat(messageInput.style.height || "0");
      isInputExpanded = determineInputExpansion(
        h,
        userInput,
        selectedFiles.length > 0,
      );
    }
  }

  function clearSelectedFiles() {
    for (const file of selectedFiles) {
      removePreview(file.id);
    }
    selectedFiles = [];
    previewUrls = {};
    objectUrlMap.clear();
    thumbnailErrors.clear();
    thumbnailErrors = new Set(thumbnailErrors); // Trigger reactivity
    const messageInput = document.getElementById(
      "messageInput",
    ) as HTMLTextAreaElement;
    if (messageInput) {
      const h = parseFloat(messageInput.style.height || "0");
      isInputExpanded = determineInputExpansion(h, userInput, false);
    }
  }

  // Setup Tauri drag-drop event listener
  let dragDropUnlisten: (() => void) | null = null;

  async function setupTauriDragDrop() {
    try {
      const webview = getCurrentWebview();
      dragDropUnlisten = await webview.onDragDropEvent((event) => {
        const eventPayload = event.payload;

        if (eventPayload.type === "over") {
          isDraggingOver = true;
        } else if (eventPayload.type === "leave") {
          isDraggingOver = false;
        } else if (eventPayload.type === "drop") {
          isDraggingOver = false;
          processFilePaths(eventPayload.paths);
        }
      });
    } catch (error) {
      console.error("Error setting up Tauri drag-drop:", error);
    }
  }

  // Fallback drag handlers for web mode
  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDraggingOver = true;
  }
  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    isDraggingOver = false;
  }
  async function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDraggingOver = false;
    if (e.dataTransfer?.files) await processFiles(e.dataTransfer.files);
  }

  $effect(() => {
    if (typeof window !== "undefined") {
      setupTauriDragDrop();
    }
    return () => {
      if (dragDropUnlisten) {
        dragDropUnlisten();
        dragDropUnlisten = null;
      }
    };
  });

  async function handlePaste(e: ClipboardEvent) {
    const items = e.clipboardData?.items;
    if (!items) return;
    const files: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const f = items[i].getAsFile();
      if (f) files.push(f);
    }
    if (files.length) {
      await processFiles(files);
      e.preventDefault();
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (showAgentSelector && filteredAgents.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        selectedAgentIndex = (selectedAgentIndex + 1) % filteredAgents.length;
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedAgentIndex =
          selectedAgentIndex === 0
            ? filteredAgents.length - 1
            : selectedAgentIndex - 1;
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        selectAgent(filteredAgents[selectedAgentIndex]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        hideAgentSelector();
      }
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }
  function resetInputUI() {
    userInput = "";
    clearSelectedFiles();
    const el = document.getElementById("messageInput") as HTMLTextAreaElement;
    if (el) resetTextareaHeight(el);
    isInputExpanded = false;
    queueMicrotask(() => {
      const el2 = document.getElementById(
        "messageInput",
      ) as HTMLTextAreaElement;
      el2?.focus();
    });
  }
  function handleSend() {
    const trimmed = trimTrailingSpace(userInput);
    if (!trimmed && selectedFiles.length === 0) return;
    const files = selectedFiles.map((sf) => ({
      id: sf.id,
      name: sf.name,
      type: sf.type,
      size: sf.size,
      dataUrl: sf.dataUrl,
      fileObject: sf.fileObject,
      filePath: sf.filePath,
    }));
    send({ text: trimmed, files, agent: selectedAgent });
    resetInputUI();
    // keep input open (removed auto-hide)
  }
  function handleTextareaInput(e: Event) {
    const el = e.target as HTMLTextAreaElement;
    const h = updateTextareaHeight(el);
    isInputExpanded = determineInputExpansion(
      h,
      userInput,
      selectedFiles.length > 0,
    );

    // Check for slash commands
    cursorPosition = el.selectionStart;
    checkForSlashCommand(el);
  }

  function checkForSlashCommand(el: HTMLTextAreaElement) {
    const textBeforeCursor = userInput.slice(0, cursorPosition);
    const lastSlashIndex = textBeforeCursor.lastIndexOf("/");

    if (lastSlashIndex !== -1) {
      const potentialCommand = textBeforeCursor.slice(lastSlashIndex);
      const commandPart = potentialCommand.split(" ")[0];

      // Only show commands if slash is at start or after whitespace
      const charBeforeSlash =
        lastSlashIndex > 0 ? textBeforeCursor[lastSlashIndex - 1] : " ";

      if (/\s/.test(charBeforeSlash) || lastSlashIndex === 0) {
        const matchingCommands = agents.filter((cmd) =>
          cmd.name.toLowerCase().startsWith(commandPart.toLowerCase()),
        );

        // Hide if a full command is typed
        if (
          matchingCommands.length === 1 &&
          matchingCommands[0].name.toLowerCase() === commandPart.toLowerCase()
        ) {
          hideAgentSelector();
          return;
        }

        if (matchingCommands.length > 0) {
          filteredAgents = matchingCommands;
          showAgentSelector = true;
          selectedAgentIndex = 0;
          return;
        }
      }
    }

    hideAgentSelector();
  }

  function selectAgent(command: { name: string; agent: AgentKey }) {
    const textBeforeCursor = userInput.slice(0, cursorPosition);
    const lastSlashIndex = textBeforeCursor.lastIndexOf("/");

    if (lastSlashIndex !== -1) {
      // Set agent and remove the typed slash command segment
      selectedAgent = command.agent;
      const potentialCommand = textBeforeCursor.slice(lastSlashIndex);
      const commandPart = potentialCommand.split(" ")[0];

      // Replace the partial command with nothing
      const beforeSlash = userInput.slice(0, lastSlashIndex);
      const afterCommand = userInput.slice(lastSlashIndex + commandPart.length);
      userInput = beforeSlash + afterCommand;

      queueMicrotask(() => {
        const el = document.getElementById(
          "messageInput",
        ) as HTMLTextAreaElement;
        if (el) {
          const newPos = beforeSlash.length;
          el.setSelectionRange(newPos, newPos);
          cursorPosition = newPos;
          el.focus();
        }
      });
    }

    hideAgentSelector();
  }

  function hideAgentSelector() {
    showAgentSelector = false;
    selectedAgentIndex = 0;
  }

  function removeSelectedAgent() {
    selectedAgent = undefined;
  }

  function startListening() {
    chatClient.startListening();
  }

  function stopListening() {
    chatClient.stopListening();
  }

  function toggleListening() {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }

  // Screenshot handling
  let showPopover = $state(false);
  let autoCaptureScreen = $state(true);
  let popoverContainer = $state<HTMLDivElement | null>(null);

  function handleDocumentClick(e: MouseEvent) {
    if (!showPopover) return;
    const target = e.target as Node;
    if (popoverContainer && !popoverContainer.contains(target)) {
      showPopover = false;
    }
  }

  function handleKeydownGlobal(e: KeyboardEvent) {
    if (e.key === 'Escape' && showPopover) {
      showPopover = false;
    }
  }

  $effect(() => {
    if (showPopover) {
      document.addEventListener('mousedown', handleDocumentClick, true);
      document.addEventListener('keydown', handleKeydownGlobal, true);
      return () => {
        document.removeEventListener('mousedown', handleDocumentClick, true);
        document.removeEventListener('keydown', handleKeydownGlobal, true);
      };
    }
  });

  // Subscribe to auto_capture_screen setting
  conversationSettings.subscribe(settings => {
    if (settings && typeof settings.auto_capture_screen === 'boolean') {
      autoCaptureScreen = settings.auto_capture_screen;
    }
  });

  async function handleScreenshotCapture() {
    try {
      const base64 = await invoke<string>('capture_screenshot_base64');
      if (base64) {
        // Save screenshot to permanent location
        const persistentPath = await saveScreenshotBase64(base64, `screenshot-${Date.now()}.png`);
        
        const screenshotAttachment = {
          id: crypto.randomUUID(),
          name: `screenshot-${Date.now()}.png`,
          type: 'image/png',
          size: base64.length * 0.75,
          filePath: persistentPath,
          dataUrl: `data:image/png;base64,${base64}`
        };
        selectedFiles = [...selectedFiles, screenshotAttachment];
        isInputExpanded = true;
        queueMicrotask(focusAndResizeTextarea);
      }
    } catch (e) {
      alert('Failed to capture screenshot');
      console.error(e);
    }
    showPopover = false;
  }

  $effect(() => {
    // GSAP animation for the input container on mount
    gsap.fromTo(
      "#chat-input-container",
      { y: 50, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.4, ease: "power2.out",  transformOrigin: "center bottom", delay: 0.2 },
    );

    // Subscribe to transcription and listening events
    const unsubscribeListeningStart = chatClient.on('listening_start', () => {
      isListening = true;
      transcriptionText = "";
    });

    const unsubscribeListeningStop = chatClient.on('listening_stop', () => {
      isListening = false;
      // Keep transcription text until final is received
    });

    const unsubscribeTranscriptionPartial = chatClient.on('transcription_partial', (text: string) => {
      if (text && isListening) {
        // Show partial transcription while listening
        userInput = text;
      }
    });

    const unsubscribeTranscriptionFinal = chatClient.on('transcription_final', (text: string) => {
      if (text) {
        // Set final transcribed text
        userInput = text;
        
        queueMicrotask(focusAndResizeTextarea);
      }
      isListening = false;
    });

    return () => {
      unsubscribeListeningStart();
      unsubscribeListeningStop();
      unsubscribeTranscriptionPartial();
      unsubscribeTranscriptionFinal();
    };
  });
</script>

<div
  id="chat-input-container"
  role="button"
  tabindex="0"
  aria-label="Drag and drop area"
  class={`fixed bottom-8 left-0 right-0 mx-auto flex-shrink-0 z-50 p-[2px] transition-all duration-300 hover:shadow-2xl w-[calc(100%-theme(spacing.8))] ${isInputExpanded ? "md:max-w-3xl": "md:max-w-xl"}  ${
    isScrolledUp
      ? "bg-gradient-to-r from-cyan-400/80 via-blue-500/80 to-purple-600/80"
      : "bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-700"
  } shadow-glow-subtle ${isDraggingOver ? "ring-4 ring-pink-500 ring-offset-2 ring-offset-black/80" : ""} rounded-4xl ${isScrolledUp ? "glassmorphic" : ""}`}
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  ondrop={handleDrop}
>
  <!-- Agent Selector Popup -->
  {#if showAgentSelector && filteredAgents.length > 0}
    <div
      class="absolute bottom-10 left-0 right-0 mb-2 bg-slate-900/80 backdrop-blur-lg rounded-xl shadow-lg max-h-50 max-w-42 overflow-y-auto z-10"
      transition:fly={{ y: 10, duration: 500 }}
    >
      {#each filteredAgents as command, index (command.name)}
        <button
          class={`w-full px-3 py-2 text-left hover:bg-slate-500/20 transition-colors border-l-2 ${
            index === selectedAgentIndex
              ? "bg-gray-500/10 border-indigo-400"
              : "border-none text-gray-300"
          }`}
          onclick={() => selectAgent(command)}
          onmouseenter={() => (selectedAgentIndex = index)}
          tabindex="-1"
        >
          <div class="flex items-center gap-3">
            {#if command.icon}
              <command.icon class="w-4 h-4 text-purple-300" />
            {/if}
            <div class="font-medium text-sm">{command.displayName}</div>
          </div>
        </button>
      {/each}
    </div>
  {/if}

  <div
    class={`flex backdrop-blur-xs px-3 py-1.5 shadow-2xl transition-all duration-300 border ${isScrolledUp ? "bg-gray-950/50 border-gray-600/30" : "bg-slate-950/95 border-gray-700/50"} rounded-4xl min-h-14 flex-col`}
  >
      <div class="flex-1 flex flex-col w-full">
        <!-- Selected agent name -->
        <div
          class="absolute -bottom-3 left-3 {selectedAgent
            ? 'visible'
            : 'invisible'}"
        >
          <button
            onclick={removeSelectedAgent}
            class="group relative rounded-full bg-violet-800/50 px-3 py-1 text-xs text-gray-200 cursor-pointer"
          >
            <span class="group-hover:opacity-20 transition-opacity">
              {#if selectedAgent === "reasoning"}
                Think
              {:else if selectedAgent === "image"}
                Image
              {/if}
            </span>
            <div
              class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <X class="w-4 h-4" />
            </div>
          </button>
        </div>

        {#if selectedFiles.length > 0}
          <div class="mb-3">
            <div class="flex flex-wrap gap-2">
              {#each selectedFiles as file (file.id)}
                <div
                  class="group relative flex items-center gap-2 bg-gray-950/60 border border-gray-700/70 rounded-xl px-3 py-2 pr-8 backdrop-blur-sm shadow-sm hover:border-gray-600 transition-colors"
                >
                  <div class="flex items-center gap-2 max-w-[200px]">
                    {#if file.type.startsWith("image/") && previewUrls[file.id] && !thumbnailErrors.has(file.id)}
                      <img
                        src={previewUrls[file.id]}
                        alt={file.name}
                        class="w-8 h-8 object-cover rounded-md border border-gray-700"
                        onerror={() => {
                          console.error('Image thumbnail failed to load:', file.name);
                          removePreview(file.id);
                          thumbnailErrors.add(file.id);
                          thumbnailErrors = new Set(thumbnailErrors); // Trigger reactivity
                        }}
                      />
                    {:else if file.type.startsWith("video/") && previewUrls[file.id] && !thumbnailErrors.has(file.id)}
                      <div class="relative">
                        <video
                          src={previewUrls[file.id]}
                          class="w-8 h-8 object-cover rounded-md border border-gray-700"
                          preload="metadata"
                          muted
                          playsinline
                          onerror={() => {
                            console.error('Video preview failed to load:', file.name);
                            removePreview(file.id);
                            thumbnailErrors.add(file.id);
                            thumbnailErrors = new Set(thumbnailErrors);
                          }}
                        ></video>
                        <div class="absolute inset-0 flex items-center justify-center bg-black/30 rounded-md">
                          <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M8 5v14l11-7z"/>
                          </svg>
                        </div>
                      </div>
                    {:else if file.type.startsWith("audio/") && previewUrls[file.id] && !thumbnailErrors.has(file.id)}
                      <audio
                        src={previewUrls[file.id]}
                        controls
                        class="w-32 h-8"
                        preload="metadata"
                        onerror={() => {
                          console.error('Audio preview failed to load:', file.name);
                          removePreview(file.id);
                          thumbnailErrors.add(file.id);
                          thumbnailErrors = new Set(thumbnailErrors);
                        }}
                      ></audio>
                    {:else}
                      {#await Promise.resolve(getIconComponent(file.type)) then Icon}
                        {#if Icon}<Icon class="w-6 h-6 text-purple-300" />{/if}
                      {/await}
                    {/if}
                    <div class="flex flex-col min-w-0">
                      <span
                        class="text-xs text-gray-200 truncate font-medium max-w-[140px]"
                        title={file.name}>{file.name}</span
                      >
                      <span class="text-[10px] text-gray-400"
                        >{file.size > 0 ? formatFileSize(file.size) : ""}</span
                      >
                    </div>
                  </div>
                  <button
                    class="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-pink-400"
                    onclick={() => removeSelectedFile(file.id)}
                    aria-label="Remove attachment"
                  >
                    <X class="w-4 h-4" />
                  </button>
                </div>
              {/each}
              {#if selectedFiles.length < MAX_ATTACHMENTS_COUNT}
                <button
                  class="flex items-center justify-center w-10 h-10 rounded-xl border border-dashed border-gray-600 text-gray-400 hover:text-purple-300 hover:border-purple-400 transition-colors"
                  onclick={openFileDialog}
                  aria-label="Add another file"
                >
                  <Paperclip class="w-5 h-5" />
                </button>
              {/if}
            </div>
          </div>
        {/if}
        <div class="flex items-center w-full">
          <!-- Plus button for popover -->
          <div class="relative mr-1 shrink-0">
            <Button
              aria-label="Add attachments"
              variant="ghost"
              size="icon"
              class="text-gray-200 hover:bg-gray-800/70 hover:text-purple-300 cursor-pointer rounded-xl"
              onclick={() => showPopover = !showPopover}
            >
              <Plus />
            </Button>
            {#if showPopover}
              <div bind:this={popoverContainer} class="absolute z-50 left-0 bottom-full mb-2 bg-gray-900/70 backdrop-blur-sm rounded-xl shadow-lg border border-gray-700 min-w-[160px] flex flex-col py-2 origin-bottom animate-fade-in ">
                <button class="flex items-center gap-2 px-4 py-2 hover:bg-gray-800/60 text-gray-200 w-full text-left" onclick={() => { openFileDialog(); showPopover = false; }}>
                    <Paperclip class="w-4 h-4" />
                  <span>Upload</span>
                </button>
                <button class="flex items-center gap-2 px-4 py-2 hover:bg-gray-800/60 text-gray-200 w-full text-left" onclick={handleScreenshotCapture}>
                  <svg class="w-4 h-4" fill="none" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg"><path d="M17.25 3C19.3211 3 21 4.67893 21 6.75V17.25C21 19.3211 19.3211 21 17.25 21H6.75C4.67893 21 3 19.3211 3 17.25V6.75C3 4.67893 4.67893 3 6.75 3H17.25ZM17.25 4.5H6.75C5.50736 4.5 4.5 5.50736 4.5 6.75V17.25C4.5 18.4926 5.50736 19.5 6.75 19.5H17.25C18.4926 19.5 19.5 18.4926 19.5 17.25V6.75C19.5 5.50736 18.4926 4.5 17.25 4.5ZM17.25 13C17.6642 13 18 13.3358 18 13.75V16C18 17.1046 17.1046 18 16 18H13.75C13.3358 18 13 17.6642 13 17.25C13 16.8358 13.3358 16.5 13.75 16.5H16C16.2761 16.5 16.5 16.2761 16.5 16V13.75C16.5 13.3358 16.8358 13 17.25 13ZM6.75 13C7.16421 13 7.5 13.3358 7.5 13.75V16C7.5 16.2761 7.72386 16.5 8 16.5H10.25C10.6642 16.5 11 16.8358 11 17.25C11 17.6642 10.6642 18 10.25 18H8C6.89543 18 6 17.1046 6 16V13.75C6 13.3358 6.33579 13 6.75 13ZM8 6H10.25C10.6642 6 11 6.33579 11 6.75C11 7.1297 10.7178 7.44349 10.3518 7.49315L10.25 7.5H8C7.75454 7.5 7.55039 7.67688 7.50806 7.91012L7.5 8V10.25C7.5 10.6642 7.16421 11 6.75 11C6.3703 11 6.05651 10.7178 6.00685 10.3518L6 10.25V8C6 6.94564 6.81588 6.08183 7.85074 6.00549L8 6H10.25H8ZM16 6C17.1046 6 18 6.89543 18 8V10.25C18 10.6642 17.6642 11 17.25 11C16.8358 11 16.5 10.6642 16.5 10.25V8C16.5 7.72386 16.2761 7.5 16 7.5H13.75C13.3358 7.5 13 7.16421 13 6.75C13 6.33579 13.3358 6 13.75 6H16Z" fill="#e5e7eb"/></svg>
                  <span>Screenshot</span>
                </button>
              </div>
            {/if}
          </div>
          <div class="relative w-full">
            {#if userInput.includes("/") && showAgentSelector}
              <div
                aria-hidden="true"
                class="w-full bg-transparent border-none text-white placeholder:text-gray-400 px-2 py-2 resize-none overflow-hidden max-h-[72px] whitespace-pre-wrap break-words pointer-events-none absolute inset-0"
                style="min-height: 40px;"
              >
                {@html highlightedInput}
              </div>
              <textarea
                id="messageInput"
                placeholder={isListening ? "Listening..." : transcriptionText ? "Processing transcription..." : "Ask anything..."}
                class={`w-full bg-transparent border-none focus:outline-none text-transparent caret-white placeholder:text-gray-400 px-2 pt-2.5 resize-none overflow-hidden  cursor-text relative z-10 ${isListening ? 'placeholder:text-blue-400' : transcriptionText ? 'placeholder:text-yellow-400' : ''}`}
                rows="3"
                bind:value={userInput}
                onkeydown={handleKeyDown}
                onpaste={handlePaste}
                style="min-height: 40px;"
                oninput={handleTextareaInput}
                onclick={(e) => {
                  cursorPosition = e.currentTarget.selectionStart;
                  checkForSlashCommand(e.currentTarget);
                }}
                onfocus={() => {
                  // Check for slash command when focusing
                  const el = document.getElementById("messageInput") as HTMLTextAreaElement;
                  if (el) {
                    cursorPosition = el.selectionStart;
                    checkForSlashCommand(el);
                  }
                }}
                disabled={isListening}
              ></textarea>
            {:else}
              <textarea
                id="messageInput"
                placeholder={isListening ? "Listening..." : transcriptionText ? "Processing transcription..." : "Ask anything..."}
                class={`w-full bg-transparent border-none focus:outline-none text-white caret-white placeholder:text-gray-400 px-2 pt-2.5 resize-none overflow-hidden  cursor-text relative z-10 ${isListening ? 'placeholder:text-blue-400' : transcriptionText ? 'placeholder:text-yellow-400' : ''}`}
                rows="1"
                bind:value={userInput}
                onkeydown={handleKeyDown}
                onpaste={handlePaste}
                style="min-height: 40px;"
                oninput={handleTextareaInput}
                onclick={(e) => {
                  cursorPosition = e.currentTarget.selectionStart;
                  checkForSlashCommand(e.currentTarget);
                }}
                onfocus={() => {
                  // Check for slash command when focusing
                  const el = document.getElementById("messageInput") as HTMLTextAreaElement;
                  if (el) {
                    cursorPosition = el.selectionStart;
                    checkForSlashCommand(el);
                  }
                }}
                disabled={isListening}
              ></textarea>
            {/if}
          </div>
          <Button
            class={`p-2 mx-1 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black/50 focus:ring-purple-400 transition-all duration-200 rounded-full shadow-xl scale-100 hover:scale-105 cursor-pointer ${
              isListening 
                ? 'bg-gradient-to-br from-red-500 to-red-600 hover:from-red-400 hover:to-red-500 animate-pulse' 
                : 'bg-transparent'
            }`}
            aria-label={isListening ? "Stop listening" : "Start voice input"}
            variant="ghost"
            size="icon"
            onclick={toggleListening}
          >
            <Mic class="h-5 w-5" />
          </Button>
          {#if isResponding}
            <Button
              variant="ghost"
              size="icon"
              class="text-red-300 hover:text-red-400 hover:bg-white/20 focus:text-red-400 ml-1 shrink-0 cursor-pointer transition-all duration-200"
              onclick={() => chatClient.interrupt()}
              aria-label="Interrupt response"
            >
              <X class="w-5 h-5 md:w-6 md:h-6" />
            </Button>
          {:else}
            <Button
              variant="ghost"
              size="icon"
              class="text-gray-300 hover:text-purple-300 hover:bg-white/20 focus:text-purple-300 ml-1 shrink-0 cursor-pointer transition-all duration-200 disabled:text-gray-500 disabled:cursor-not-allowed"
              disabled={!userInput.trim() && selectedFiles.length === 0}
              onclick={handleSend}
              aria-label="Send message"
            >
              <Send class="w-5 h-5 md:w-6 md:h-6" />
            </Button>
          {/if}
        </div>
        
        <!-- Transcription indicator -->
        <!-- {#if transcriptionText && isListening}
          <div class="mt-2 px-2 py-1 bg-blue-500/20 border border-blue-400/30 rounded-lg">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
              <span class="text-sm text-blue-300 italic">"{transcriptionText}"</span>
            </div>
          </div>
        {/if} -->
      </div>
  </div>
</div>

<style>
  :global(.glassmorphic) {
    background: linear-gradient(
      135deg,
      rgba(99, 102, 241, 0.1),
      rgba(168, 85, 247, 0.1),
      rgba(236, 72, 153, 0.1)
    );
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.3),
      0 0 20px rgba(56, 189, 248, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.1);
  }
  :global(.glassmorphic:hover) {
    background: linear-gradient(
      135deg,
      rgba(99, 102, 241, 0.15),
      rgba(168, 85, 247, 0.15),
      rgba(236, 72, 153, 0.15)
    );
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow:
      0 8px 32px rgba(0, 0, 0, 0.4),
      0 0 25px rgba(56, 189, 248, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.15);
  }
  :global(textarea::placeholder) {
    color: #9ca3af !important;
    opacity: 1;
  }
  :global(textarea:focus::placeholder) {
    color: #6b7280 !important;
  }
</style>
