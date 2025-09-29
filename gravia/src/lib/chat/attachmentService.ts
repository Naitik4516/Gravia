
// src/lib/attachmentService.ts
import type { FileAttachment } from './types';

export const MAX_TOTAL_ATTACHMENT_SIZE = 50 * 1024 * 1024; // 50 MB
export const MAX_ATTACHMENTS_COUNT = 10;

export const ALLOWED_MIME_TYPES = new Set([
  // Document formats
  'application/pdf',
  'application/msword', // .doc
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  'application/vnd.ms-excel', // .xls
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
  'application/vnd.oasis.opendocument.text', // .odt
  'application/rtf', 'text/rtf', // .rtf
  
  // Code and markup formats
  'application/x-javascript', 'text/javascript',
  'application/x-python', 'text/x-python',
  'text/plain', // .txt
  'text/html', // .html
  'text/css', // .css
  'text/markdown', 'text/x-markdown', // .md
  'text/csv', // .csv
  'text/xml', 'application/xml', // .xml
  'application/json', // .json
  'text/x-csharp', // .cs
  'text/x-c++src', 'text/x-c', // .cpp, .c
  'text/x-java', // .java
  'text/x-typescript', // .ts
  'text/x-swift', // .swift
  'application/x-sh', 'application/x-bat', // .sh, .bat
  'text/x-php', // .php
  'text/x-ruby', // .rb
  'text/x-go', // .go
  'text/x-rust', // .rs
  'text/x-sql', // .sql
  'text/yaml', // .yaml, .yml
  
  // Web formats
  'application/wasm', // .wasm
  'text/jsx', // .jsx
  'text/tsx', // .tsx
  'application/vnd.coffeescript', // .coffee
  'text/x-sass', 'text/x-scss', // .sass, .scss
  'application/x-httpd-php', // .php
  
  // Image formats
  'image/png', // .png
  'image/jpeg', // .jpg, .jpeg
  'image/webp', // .webp
  'image/svg+xml', // .svg
  'image/heic',
  'image/heif',
  'image/bmp', // .bmp
  'image/tiff', // .tif, .tiff
  'image/x-icon', 'image/vnd.microsoft.icon', // .ico
  
  // Video formats
  'video/mp4',
  'video/mpeg',
  'video/quicktime', // .mov
  'video/x-msvideo', // .avi
  'video/x-flv',
  'video/webm',
  'video/x-ms-wmv',
  'video/3gpp', 'audio/3gpp',
  
  // Audio formats
  'audio/wav', 'audio/x-wav',
  'audio/mpeg', // .mp3
  'audio/aiff', 'audio/x-aiff',
  'audio/aac',
  'audio/ogg',
  'audio/flac', 'audio/x-flac',
  
]);

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Processes a list of files, validating them and preparing them for attachment.
 * Returns a promise that resolves to an array of processed FileAttachment objects and a list of errors.
 */
export async function processFilesForAttachment(
  filesToProcess: File[],
  currentSelectedFiles: FileAttachment[],
  currentTotalSize: number
): Promise<{ newAttachments: FileAttachment[], errors: string[] }> {
  const newAttachments: FileAttachment[] = [];
  const errors: string[] = [];
  let updatedTotalSize = currentTotalSize;

  for (const file of filesToProcess) {
    if (currentSelectedFiles.length + newAttachments.length >= MAX_ATTACHMENTS_COUNT) {
      errors.push(`You can attach a maximum of ${MAX_ATTACHMENTS_COUNT} files.`);
      break;
    }
    if (!ALLOWED_MIME_TYPES.has(file.type)) {
      errors.push(`File type ${file.type || 'unknown'} is not allowed for ${file.name}.`);
      continue;
    }
    if (updatedTotalSize + file.size > MAX_TOTAL_ATTACHMENT_SIZE) {
      errors.push(`Cannot add ${file.name}, total attachment size would exceed ${MAX_TOTAL_ATTACHMENT_SIZE / (1024 * 1024)}MB.`);
      continue;
    }

    updatedTotalSize += file.size;
    const fileId = crypto.randomUUID();
    const attachment: FileAttachment = {
      id: fileId,
      name: file.name,
      type: file.type,
      size: file.size,
      fileObject: file,
    };

    if (file.type.startsWith("image/")) {
      try {
        attachment.dataUrl = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => resolve(e.target?.result as string);
          reader.onerror = (e) => reject(e);
          reader.readAsDataURL(file);
        });
      } catch (error) {
        console.error("Error reading image file for preview:", error);
        errors.push(`Could not generate preview for image ${file.name}.`);
        // Optionally, still add the file without a preview or skip it
      }
    }
    newAttachments.push(attachment);
  }
  return { newAttachments, errors };
}
