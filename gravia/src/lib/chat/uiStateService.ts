// src/lib/uiStateService.ts
import {
  Paperclip,
  FileText,
  FileCode2 as FileCode, // Renamed to avoid conflict if FileCode is a type
  FileImage,
  Video as FileVideo,
  FileAudio,
  FileSpreadsheet,
  FileSliders,
  FileCog,
  FileJson,
  FileArchive,
  FileType,
  FileBadge,
  FileX,
  FileSearch,
  Database,
} from "@lucide/svelte";

/**
 * Get the appropriate Lucide icon component for a given MIME type.
 */
export function getIconComponent(mimeType: string) {
  if (!mimeType) return Paperclip;

  const type = mimeType.toLowerCase();

  // Image files
  if (type.startsWith("image/")) return FileImage;
  
  // Video files
  if (type.startsWith("video/")) return FileVideo;
  
  // Audio files
  if (type.startsWith("audio/")) return FileAudio;
  
  // Document types
  if (type.includes("spreadsheet") || type.includes("excel") || type === "text/csv") 
    return FileSpreadsheet;
  
  if (type.includes("presentation") || type.includes("powerpoint") || type.includes("slide")) 
    return FileSliders;
    
  if (type.includes("wordprocessing") || type.includes("msword") || type.includes("opendocument.text"))
    return FileText;

  // Archive types
  if (type.includes("zip") || type.includes("tar") || type.includes("compressed") || 
      type.includes("gzip") || type.includes("7z") || type.includes("bzip2"))
    return FileArchive;

  switch (type) {
    // Documents
    case "application/pdf":
      return FileText;
    case "text/plain":
    case "text/rtf":
    case "application/rtf":
    case "text/markdown":
    case "text/x-markdown":
      return FileText;
      
    // Data files
    case "application/json":
    case "text/yaml":
      return FileJson;
    case "text/csv":
      return FileSpreadsheet;
    case "text/xml":
    case "application/xml":
      return FileCode;
      
    // Database
    case "text/x-sql":
      return Database;
      
    // Code files
    case "text/html":
    case "text/css":
    case "application/x-javascript":
    case "text/javascript":
    case "application/x-python":
    case "text/x-python":
    case "text/x-typescript":
    case "text/x-csharp":
    case "text/x-c++src":
    case "text/x-c":
    case "text/x-java":
    case "text/x-swift":
    case "text/x-php":
    case "application/x-httpd-php":
    case "text/x-ruby":
    case "text/x-go":
    case "text/x-rust":
    case "text/jsx":
    case "text/tsx":
    case "application/vnd.coffeescript":
    case "text/x-sass":
    case "text/x-scss":
      return FileCode;
      
    // Shell scripts
    case "application/x-sh":
    case "application/x-bat":
      return FileCog;
      
    // Web assembly
    case "application/wasm":
      return FileType;
      
    default:
      // Check file extension patterns
      if (type.startsWith("text/x-")) return FileCode; // Custom text types assumed to be code
      if (type.includes("document")) return FileText; // Any other document types
      if (type.includes("application/vnd.")) return FileBadge; // Other vendor-specific formats
      
      return Paperclip;
  }
}

/**
 * Calculate whether the input area should be shown as expanded 
 * based on textarea height and file attachments
 */
// Hysteresis thresholds to prevent flicker when text length oscillates around a breakpoint
const EXPAND_HEIGHT_THRESHOLD = 48; // expand when height grows beyond this
const COLLAPSE_HEIGHT_THRESHOLD = 44; // collapse only when height shrinks below this

let lastExpanded = false;

export function determineInputExpansion(
  textareaHeight: number,
  userInput: string,
  hasAttachments: boolean
): boolean {
  // Always expanded if there are attachments
  if (hasAttachments) {
    lastExpanded = true;
    return true;
  }

  // Multi-line (newline present) => expand
  if (userInput.includes('\n')) {
    lastExpanded = true;
    return true;
  }

  // Apply hysteresis around height thresholds
  if (lastExpanded) {
    if (textareaHeight < COLLAPSE_HEIGHT_THRESHOLD) {
      lastExpanded = false;
    }
  } else {
    if (textareaHeight > EXPAND_HEIGHT_THRESHOLD) {
      lastExpanded = true;
    }
  }

  return lastExpanded;
}

/**
 * Get textarea height based on content
 * Returns a new height value without actually modifying the element
 */
export function calculateTextareaHeight(element: HTMLTextAreaElement): number {
  // Store original height
  const originalHeight = element.style.height;
  
  // Reset height temporarily to auto to get proper scrollHeight
  element.style.height = 'auto';
  
  // Get scrollHeight and apply maximum constraint
  const newHeight = Math.min(element.scrollHeight, 72); // Max height 72px (approx 3 lines)
  
  // Restore original height
  element.style.height = originalHeight;
  
  return newHeight;
}

/**
 * Applies the calculated height to a textarea element and returns the new height
 */
export function updateTextareaHeight(element: HTMLTextAreaElement): number {
  element.style.height = 'auto';
  const newHeight = Math.min(element.scrollHeight, 72); // Max height 72px (approx 3 lines)
  element.style.height = `${newHeight}px`;
  return newHeight;
}

/**
 * Reset textarea height to single line
 */
export function resetTextareaHeight(element: HTMLTextAreaElement): void {
  element.style.height = 'auto';
  const singleLineHeight = Math.max(parseInt(getComputedStyle(element).minHeight), element.scrollHeight);
  element.style.height = `${Math.min(singleLineHeight, 40)}px`;
}

/**
 * Remove trailing whitespace only (preserve internal spaces)
 */
export function trimTrailingSpace(text: string): string {
  return text.replace(/\s+$/, '');
}