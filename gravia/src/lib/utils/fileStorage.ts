import { appDataDir, join } from "@tauri-apps/api/path";
import { copyFile, exists, mkdir, writeFile } from "@tauri-apps/plugin-fs";

let cachedScreenshotDir: Promise<string> | null = null;

async function ensureScreenshotDir(): Promise<string> {
  if (!cachedScreenshotDir) {
    cachedScreenshotDir = (async () => {
      const baseDir = await appDataDir();
      const screenshotsDir = await join(baseDir, "screenshots");
      if (!(await exists(screenshotsDir))) {
        await mkdir(screenshotsDir, { recursive: true });
      }
      return screenshotsDir;
    })();
  }

  return cachedScreenshotDir;
}

function base64ToBytes(base64: string): Uint8Array {
  const normalized = base64.replace(/\r?\n/g, "");
  const binary = atob(normalized);
  const length = binary.length;
  const bytes = new Uint8Array(length);

  for (let i = 0; i < length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return bytes;
}

export async function saveScreenshotBase64(base64: string, name?: string): Promise<string> {
  const dir = await ensureScreenshotDir();
  const fileName = name ?? `screenshot-${Date.now()}-${crypto.randomUUID()}.png`;
  const filePath = await join(dir, fileName);
  await writeFile(filePath, base64ToBytes(base64));
  return filePath;
}

export async function migrateTempFileToScreenshots(originalPath: string): Promise<string | null> {
  try {
    const lowerPath = originalPath.toLowerCase();
    if (!lowerPath.includes("\\appdata\\local\\temp") && !lowerPath.includes("/temp/")) {
      return originalPath;
    }

    const dir = await ensureScreenshotDir();
    const fileName = originalPath.split(/[/\\]/).pop() ?? `screenshot-${Date.now()}.png`;
    const destination = await join(dir, fileName);

    if (!(await exists(destination))) {
      await copyFile(originalPath, destination);
    }

    return destination;
  } catch (error) {
    console.error("Failed to migrate screenshot to persistent storage", error);
    return null;
  }
}
