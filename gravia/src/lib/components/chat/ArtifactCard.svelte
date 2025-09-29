<script lang="ts">
  import { File, ExternalLink } from "@lucide/svelte";
  import { openPath  } from '@tauri-apps/plugin-opener';
  import { toast } from "svelte-sonner";

  let {
    artifact
  }: {
    artifact: { name: string; path: string; data_b64?: string; };
  } = $props();

  let isOpening = $state(false);

  async function openArtifact() {
    if (isOpening) return;
    
    isOpening = true;
    try {
      await openPath(artifact.path);
      toast.success(`Opened ${artifact.name}`);
    } catch (error) {
      console.error('Failed to open artifact:', error);
      toast.error(`Failed to open file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      isOpening = false;
    }
  }

  function getFileExtension(filename: string): string {
    return filename.split('.').pop()?.toLowerCase() || '';
  }

  function getFileSize(path: string): string {
    // Since we don't have file size info, we'll just show the extension
    return getFileExtension(artifact.name).toUpperCase();
  }
</script>

<button class="artifact-card bg-gradient-to-r from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-lg p-4 hover:from-indigo-600/30 hover:to-purple-600/30 transition-all duration-200 cursor-pointer {isOpening ? 'opacity-50 pointer-events-none' : ''}" onclick={openArtifact}>
  <div class="flex items-center gap-3">
    <div class="flex-shrink-0 w-10 h-10 bg-indigo-500/30 rounded-lg flex items-center justify-center">
      <File class="w-5 h-5 text-indigo-300" />
    </div>
    
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2">
        <h3 class="text-sm font-semibold text-gray-200 truncate">
          {artifact.name}
        </h3>
        <ExternalLink class="w-4 h-4 text-gray-400 flex-shrink-0" />
      </div>
      
      <div class="flex items-center gap-2 mt-1">
        <span class="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-1 rounded">
          {getFileSize(artifact.path)}
        </span>
        <span class="text-xs text-gray-400">
          {isOpening ? 'Opening...' : 'Generated Artifact'}
        </span>
      </div>
    </div>
  </div>
  
  <div class="mt-3 text-xs text-gray-500 truncate">
    {artifact.path}
  </div>
</button>

<style>
  .artifact-card:hover {
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
  }
</style>