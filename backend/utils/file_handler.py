from typing import List, Tuple
import mimetypes
import time
import re
import base64
from urllib.parse import urlparse
from pathlib import Path

from fastapi import HTTPException

from agno.agent import Agent
from agno.media import Audio, Image, Video, File
from agno.utils.log import logger
from event_handler import send_event

class UnsupportedFileTypeError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
# MIME type groups (DRY centralization)
IMAGE_MIME_TYPES = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml",
    "image/heic", "image/heif", "image/bmp", "image/tiff", "image/x-icon", "image/vnd.microsoft.icon"
}
AUDIO_MIME_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mp3", "audio/mpeg", "audio/aiff", "audio/x-aiff", "audio/aac",
    "audio/ogg", "audio/flac", "audio/x-flac", "audio/3gpp"
}
VIDEO_MIME_TYPES = {
    "video/x-flv", "video/quicktime", "video/mpeg", "video/mpegs", "video/mpgs", "video/mpg", "video/mp4",
    "video/webm", "video/wmv", "video/3gpp", "video/x-msvideo", "video/x-ms-wmv"
}
DOCUMENT_MIME_TYPES = {
    # PDF
    "application/pdf",
    # Word
    "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Excel
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # OpenDocument
    "application/vnd.oasis.opendocument.text",
    # RTF
    "application/rtf", "text/rtf",
    # CSV
    "text/csv",
    # Text & code
    "text/plain", "text/html", "text/css", "text/markdown", "text/x-markdown", "text/xml", "application/xml",
    "text/x-csharp", "text/x-c++src", "text/x-c", "text/x-java", "text/x-typescript", "text/x-swift",
    "text/x-php", "text/x-ruby", "text/x-go", "text/x-rust", "text/x-sql", "text/yaml", "application/x-javascript",
    "text/javascript", "application/x-python", "text/x-python", "application/x-sh", "application/x-bat", "text/jsx",
    "text/tsx", "application/vnd.coffeescript", "text/x-sass", "text/x-scss", "application/x-httpd-php",
    # JSON
    "application/json"
}

MEDIA_KIND_IMAGE = "image"
MEDIA_KIND_AUDIO = "audio"
MEDIA_KIND_VIDEO = "video"
MEDIA_KIND_DOCUMENT = "document"

# Constants
MAX_INLINE_SIZE = 20 * 1024 * 1024  # 20 MB in bytes total budget
INLINE_SAFETY_BUFFER = 256 * 1024    # 256 KB buffer to avoid edge overflow


def classify_mime(content_type: str) -> str:
    if content_type in IMAGE_MIME_TYPES:
        return MEDIA_KIND_IMAGE
    if content_type in AUDIO_MIME_TYPES:
        return MEDIA_KIND_AUDIO
    if content_type in VIDEO_MIME_TYPES:
        return MEDIA_KIND_VIDEO
    if content_type in DOCUMENT_MIME_TYPES:
        return MEDIA_KIND_DOCUMENT
    return "unsupported"


class FileMeta:
    def __init__(self, path: Path):
        self.path = path
        self.size = path.stat().st_size if path.exists() else 0
        self.content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.kind = classify_mime(self.content_type)


async def _upload_if_needed(path: Path, model, remaining_inline_budget: int) -> Tuple[str, int, bool]:
    """Return a filepath or uploaded identifier.
    Returns (reference, size_counted_inline, used_upload)
    If size fits remaining_inline_budget, we keep it inline (no upload) and count its size.
    If not and model provided, attempt upload (returns logical handle, counts 0 inline).
    If not and no model, still inline (best-effort) - may overflow.
    """
    size = path.stat().st_size
    if size <= remaining_inline_budget:
        return str(path), size, False
    if model is None:
        # No model => cannot upload; return inline anyway (caller might warn)
        return str(path), size, False
    try:
        logger.info(f"Uploading (budget overflow) file: {path}")
        await send_event("Uploading file...")
        uploaded = model.get_client().files.upload(
            file=path,
            config=dict(name=path.stem, display_name=path.stem),
        )
        while uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = model.get_client().files.get(name=uploaded.name)
        logger.info(f"Uploaded file: {uploaded}")
        await send_event("File uploaded")
        return uploaded.name, 0, True
    except Exception as e:
        logger.error(f"Upload failed for {path}: {e}; using inline fallback")
        return str(path), size, False


def _make_media(meta: FileMeta, ref: str):
    if meta.kind == MEDIA_KIND_IMAGE:
        return Image(filepath=ref)
    if meta.kind == MEDIA_KIND_AUDIO:
        return Audio(filepath=ref)
    if meta.kind == MEDIA_KIND_VIDEO:
        return Video(filepath=ref)
    if meta.kind == MEDIA_KIND_DOCUMENT:
        return File(filepath=ref)
    raise UnsupportedFileTypeError(f"Unsupported file type: {meta.content_type}")


def _infer_url_kind(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or '').lower()
    path = parsed.path.lower()
    # Basic heuristic for image extensions
    if any(path.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"]):
        return MEDIA_KIND_IMAGE
    if any(path.endswith(ext) for ext in [".mp3", ".wav", ".ogg", ".flac", ".aac"]):
        return MEDIA_KIND_AUDIO
    if any(path.endswith(ext) for ext in [".mp4", ".webm", ".mov", ".avi", ".mkv"]):
        return MEDIA_KIND_VIDEO
    if host in YOUTUBE_HOSTS:
        return MEDIA_KIND_VIDEO
    # Default treat as document/file
    return MEDIA_KIND_DOCUMENT


URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)
DATA_URL_REGEX = re.compile(r"data:([^;]+);base64,([A-Za-z0-9+/]+=*)", re.IGNORECASE)
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}


def parse_data_url(data_url: str) -> Tuple[str, bytes]:
    """
    Parse a data URL and return (mime_type, decoded_data).
    Returns None if the data URL is invalid.
    """
    match = DATA_URL_REGEX.match(data_url.strip())
    if not match:
        raise ValueError(f"Invalid data URL format: {data_url[:50]}...")
    
    mime_type = match.group(1)
    base64_data = match.group(2)
    
    try:
        decoded_data = base64.b64decode(base64_data)
        return mime_type, decoded_data
    except Exception as e:
        raise ValueError(f"Failed to decode base64 data: {e}")


def classify_data_url_mime(mime_type: str) -> str:
    """Classify a MIME type from a data URL into our media categories."""
    return classify_mime(mime_type)


def create_media_from_data_url(data_url: str):
    """Create appropriate media object from a data URL."""
    try:
        mime_type, decoded_data = parse_data_url(data_url)
        media_kind = classify_data_url_mime(mime_type)
        
        if media_kind == MEDIA_KIND_IMAGE:
            return Image(content=decoded_data, mime_type=mime_type)
        elif media_kind == MEDIA_KIND_AUDIO:
            return Audio(content=decoded_data, mime_type=mime_type)
        elif media_kind == MEDIA_KIND_VIDEO:
            return Video(content=decoded_data, mime_type=mime_type)
        elif media_kind == MEDIA_KIND_DOCUMENT:
            return File(content=decoded_data, mime_type=mime_type)
        else:
            raise UnsupportedFileTypeError(f"Unsupported data URL MIME type: {mime_type}")
    except Exception as e:
        logger.error(f"Failed to process data URL: {e}")
        raise UnsupportedFileTypeError(f"Invalid data URL: {e}")


def extract_data_urls_from_text(text: str):
    """Extract data URLs from text and return categorized media objects."""
    data_urls = DATA_URL_REGEX.findall(text or "")
    images: List[Image] = []
    audios: List[Audio] = []
    videos: List[Video] = []
    documents: List[File] = []
    
    # Reconstruct full data URLs and process them
    for mime_type, base64_data in data_urls:
        try:
            decoded_data = base64.b64decode(base64_data)
            media_kind = classify_data_url_mime(mime_type)
            if media_kind == MEDIA_KIND_IMAGE:
                images.append(Image(content=decoded_data, mime_type=mime_type))
            elif media_kind == MEDIA_KIND_AUDIO:
                audios.append(Audio(content=decoded_data, mime_type=mime_type))
            elif media_kind == MEDIA_KIND_VIDEO:
                videos.append(Video(content=decoded_data, mime_type=mime_type))
            elif media_kind == MEDIA_KIND_DOCUMENT:
                documents.append(File(content=decoded_data, mime_type=mime_type))
        except Exception as e:
            logger.warning(f"Skipping invalid data URL with MIME type {mime_type}: {e}")
            continue
    
    return images, audios, videos, documents


def extract_media_from_text(text: str):
    """Extract both regular URLs and data URLs from text and return categorized media objects."""
    # Extract regular URLs
    urls = URL_REGEX.findall(text or "")
    images: List[Image] = []
    audios: List[Audio] = []
    videos: List[Video] = []
    documents: List[File] = []
    seen = set()
    
    # Process regular URLs
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        kind = _infer_url_kind(u)
        if kind == MEDIA_KIND_IMAGE:
            images.append(Image(url=u))
        elif kind == MEDIA_KIND_AUDIO:
            audios.append(Audio(url=u))
        elif kind == MEDIA_KIND_VIDEO:
            videos.append(Video(url=u))
        elif kind == MEDIA_KIND_DOCUMENT:
            documents.append(File(url=u))
    
    # Extract and process data URLs
    data_images, data_audios, data_videos, data_documents = extract_data_urls_from_text(text)
    
    # Combine results
    images.extend(data_images)
    audios.extend(data_audios)
    videos.extend(data_videos)
    documents.extend(data_documents)
    
    return images, audios, videos, documents


async def process_file(
    filepaths: List[Path],
    agent: Agent,
) -> Tuple[List[Image], List[Audio], List[Video], List[File]]:
    metas: List[FileMeta] = []
    
    await send_event("Processing files...")

    for fp in filepaths:
        if isinstance(fp, str):
            fp = Path(fp)
        if not fp.exists() or not fp.is_file():
            raise HTTPException(status_code=400, detail=f"File not found: {fp}")
        meta = FileMeta(fp)
        if meta.kind == "unsupported":
            raise UnsupportedFileTypeError(f"Unsupported file type: {meta.content_type}")
        metas.append(meta)

    # Sort by size ascending so smaller files preferentially stay inline
    metas.sort(key=lambda m: m.size)

    inline_budget = MAX_INLINE_SIZE - INLINE_SAFETY_BUFFER
    used_inline = 0

    images: List[Image] = []
    audios: List[Audio] = []
    videos: List[Video] = []
    documents: List[File] = []

    for meta in metas:
        ref, counted, uploaded = await _upload_if_needed(meta.path, agent, inline_budget - used_inline)
        used_inline += counted
        media_obj = _make_media(meta, ref)
        if meta.kind == MEDIA_KIND_IMAGE:
            images.append(media_obj)  # type: ignore[arg-type]
        elif meta.kind == MEDIA_KIND_AUDIO:
            audios.append(media_obj)  # type: ignore[arg-type]
        elif meta.kind == MEDIA_KIND_VIDEO:
            videos.append(media_obj)  # type: ignore[arg-type]
        elif meta.kind == MEDIA_KIND_DOCUMENT:
            documents.append(media_obj)  # type: ignore[arg-type]
        logger.info(
            f"Prepared {meta.kind} {meta.path.name} | size={meta.size} | inline_counted={counted>0} | "
            f"uploaded={uploaded} | total_inline_used={used_inline}/{inline_budget}"
        )

    await send_event("Responding...")
    return images, audios, videos, documents