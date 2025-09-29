import asyncio
import edge_tts
from fastapi import WebSocket
import pyaudio
import io
import threading
import time
from queue import Queue
from pydub import AudioSegment
from utils.data_handler import settings
from typing import Optional, Tuple
import re
import html

class PyAudioStreamer:
    """Low-level PCM playback helper for continuous raw PCM streaming."""

    def __init__(self, rate: int = 24000, channels: int = 1, sample_width: int = 2):
        self.audio = pyaudio.PyAudio()
        self.audio_queue: Queue[Optional[bytes]] = Queue()
        self.stream = None
        self.target_rate = rate
        self.target_channels = channels
        self.target_sample_width = sample_width
        self.frame_size = self.target_channels * self.target_sample_width
        self.chunk_buffer = b""
        # PCM write granularity (moderate size to balance latency vs overhead)
        self.fixed_chunk_size = 3072
        self._playback_thread: Optional[threading.Thread] = None
        self._started = False
        self.is_raw_pcm = False
        # Backpressure config
        self.max_queue_chunks = 80
        # Status tracking
        self.is_playing = False
        self.tts_manager: Optional['TTSManager'] = None  # Will be set by TTSManager

    def _ensure_stream(self):
        if self.stream is None:
            self.stream = self.audio.open(
                format=self.audio.get_format_from_width(self.target_sample_width),
                channels=self.target_channels,
                rate=self.target_rate,
                output=True,
                frames_per_buffer=2048,
            )

    def _play_audio_worker(self):
        while True:
            chunk_data = self.audio_queue.get()
            if chunk_data is None:
                self.audio_queue.task_done()
                self.is_playing = False
                if self.tts_manager:
                    self.tts_manager.is_playing = False
                break
            try:
                if not self.is_playing:
                    self.is_playing = True
                    if self.tts_manager:
                        self.tts_manager.is_playing = True
                
                raw_data = chunk_data if self.is_raw_pcm else self._decode_mp3(chunk_data)
                self.chunk_buffer += raw_data
                while len(self.chunk_buffer) >= self.fixed_chunk_size:
                    to_write = self.chunk_buffer[: self.fixed_chunk_size]
                    self.chunk_buffer = self.chunk_buffer[self.fixed_chunk_size:]
                    if len(to_write) % self.frame_size:
                        pad = self.frame_size - (len(to_write) % self.frame_size)
                        to_write += b"\x00" * pad
                    if self.stream:
                        self.stream.write(to_write)
            except Exception as e:
                print(f"[TTS] Playback error: {e}")
            finally:
                self.audio_queue.task_done()
                # Check if queue is empty after processing this chunk
                if self.audio_queue.empty():
                    self.is_playing = False
                    if self.tts_manager:
                        self.tts_manager.is_playing = False

    def _decode_mp3(self, data: bytes) -> bytes:
        seg = AudioSegment.from_mp3(io.BytesIO(data))
        seg = seg.set_frame_rate(self.target_rate)
        seg = seg.set_channels(self.target_channels)
        seg = seg.set_sample_width(self.target_sample_width)
        return seg.raw_data

    def start(self):
        if self._started:
            return
        self._ensure_stream()
        self._playback_thread = threading.Thread(target=self._play_audio_worker, daemon=True)
        self._playback_thread.start()
        self._started = True

    def add_chunk(self, data: bytes):
        self.start()
        while self.audio_queue.qsize() > self.max_queue_chunks:
            time.sleep(0.002)
        self.audio_queue.put(data)

    def drain(self):
        self.audio_queue.join()

    def stop(self):
        try:
            if self.chunk_buffer and self.stream:
                if len(self.chunk_buffer) % self.frame_size:
                    pad = self.frame_size - (len(self.chunk_buffer) % self.frame_size)
                    self.chunk_buffer += b"\x00" * pad
                try:
                    self.stream.write(self.chunk_buffer)
                except Exception:
                    pass
            self.chunk_buffer = b""
            if self._started:
                self.audio_queue.put(None)
                self.audio_queue.join()
        finally:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
            try:
                self.audio.terminate()
                self.audio = pyaudio.PyAudio()
                self.stream = None
            except Exception:
                pass
            self._started = False


class TTSManager:
    """Serializes TTS synthesis & overlaps next synthesis (prefetch) to reduce gaps."""

    def __init__(self):
        # Use higher internal playback rate for better quality (edge voices often 24k or 48k)
        self.streamer = PyAudioStreamer(rate=24000, channels=1, sample_width=2)
        self.queue: asyncio.Queue[Tuple[WebSocket, str]] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.current_cancel_event = asyncio.Event()
        self.lock = asyncio.Lock()
        
        # Cache voice settings and pre-initialize
        self.cached_voice = None
        self.voice_last_update = 0
        
        # Status tracking for TTS activity
        self.is_synthesizing = False
        self.is_playing = False
        self.synthesis_task: Optional[asyncio.Task] = None
        
        # Text buffering for short chunks
        self.text_buffer = ""
        self.buffer_ws: Optional[WebSocket] = None
        self.last_chunk_time = 0
        self.buffer_flush_task: Optional[asyncio.Task] = None
        
        # Configurable thresholds for chunk processing
        self.min_words = 3  # Minimum words before processing
        self.min_chars = 15  # Minimum characters before processing
        self.buffer_timeout = 1.5  # Seconds to wait before flushing incomplete buffer
        
        # Pre-warm audio stream
        self.streamer.tts_manager = self
        self.streamer.start()

    def get_voice(self):
        """Get cached voice or refresh if settings changed."""
        current_time = asyncio.get_event_loop().time()
        if self.cached_voice is None or (current_time - self.voice_last_update) > 30:  # Cache for 30s
            voice_setting = settings.get("voice", "en-US-JennyNeural")
            self.cached_voice = (
                "en-US-AvaMultilingualNeural"
                if voice_setting == "default"
                else voice_setting
            )
            self.voice_last_update = current_time
        return self.cached_voice or "en-US-JennyNeural"

    def _clean_text(self, text: str) -> str:
        """Lightweight cleaning: remove markdown/HTML/emojis and normalize math/prose for TTS."""
        if not text:
            return ""
        # Unescape HTML entities
        text = html.unescape(text)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove markdown tokens conservatively (preserve math operators)
        # - Blockquotes at start of line
        text = re.sub(r"(?m)^\s*>+\s?", "", text)
        # - List bullets at start of line (-, +, *)
        text = re.sub(r"(?m)^\s*[-+*]\s+", "", text)
        # - Bold/underline/backticks; keep single '*' for math
        text = re.sub(r"\*\*|__|`+", "", text)
        # - Headings at start of line
        text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
        # Keep links and include URL: [text](url) -> "text (url)"
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
        # Normalize LaTeX/markdown math to readable phrases
        text = self._normalize_math(text)
        # Replace numeric ranges 2024-2025 with "to"
        text = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " to ", text)
        # Strip emojis (common ranges)
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub(r"", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _normalize_math(self, text: str) -> str:
        """Convert simple math notations to TTS-friendly phrases.

        Handles:
        - Inline math delimiters: removes '$'
        - Caret exponents: x^2, 10^8, x^{n}
        - Standalone exponents: ^2 -> "squared", ^8 -> "raised to the power 8"
        - Unicode superscripts: x², 10⁸, xⁿ
        """
        if not text:
            return text

        # Remove inline math dollar delimiters
        if '$' in text:
            text = text.replace('$', '')

        # Handle \frac{num}{den} -> "num over den"
        frac_pattern = re.compile(r"\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}")
        text = frac_pattern.sub(lambda m: f"{m.group(1)} over {m.group(2)}", text)

        # Remove sizing wrappers like \left \right
        text = re.sub(r"\\left\s*", "", text)
        text = re.sub(r"\\right\s*", "", text)

        # Strip LaTeX formatting wrappers but keep content, e.g., \boxed{X} -> X
        wrapper_cmds = (
            "boxed", "text", "operatorname", "mathrm", "mathbf", "mathit",
            "mathbb", "mathcal", "textrm", "textbf", "textit"
        )
        wrapper_pattern = re.compile(r"\\(" + "|".join(map(re.escape, wrapper_cmds)) + r")\s*\{([^{}]+)\}")
        for _ in range(3):
            if not wrapper_pattern.search(text):
                break
            text = wrapper_pattern.sub(lambda m: m.group(2), text)

        # Map common LaTeX greek letters and functions to plain words
        latex_map = {
            r"\\pi": "pi", r"\\theta": "theta", r"\\alpha": "alpha", r"\\beta": "beta",
            r"\\gamma": "gamma", r"\\delta": "delta", r"\\lambda": "lambda", r"\\mu": "mu",
            r"\\nu": "nu", r"\\phi": "phi", r"\\psi": "psi", r"\\omega": "omega",
            r"\\sin": "sin", r"\\cos": "cos", r"\\tan": "tan", r"\\log": "log", r"\\ln": "ln"
        }
        for pat, rep in latex_map.items():
            text = re.sub(pat, rep, text)

        # Remove stray backslashes before letters (e.g., \x -> x)
        text = re.sub(r"\\([A-Za-z])", r"\1", text)

        # 1) Normalize caret forms like base^exp or base^{exp}
        caret_pattern = re.compile(r"(?P<base>[A-Za-z0-9_.()\[\])]+)\s*\^\s*(?P<exp>\{[^}]+\}|[A-Za-z0-9]+)")

        def caret_repl(m: re.Match) -> str:
            base = m.group('base')
            exp = m.group('exp')
            if exp.startswith('{') and exp.endswith('}'):
                exp = exp[1:-1].strip()
            if exp == '2':
                return f"{base} squared"
            if exp == '3':
                return f"{base} cubed"
            return f"{base} raised to the power {exp}"

        text = caret_pattern.sub(caret_repl, text)

        # 2) Standalone ^exp (no explicit base)
        standalone_caret = re.compile(r"\^\s*(\{[^}]+\}|\d+|[A-Za-z]+)")

        def standalone_repl(m: re.Match) -> str:
            exp = m.group(1)
            if exp.startswith('{') and exp.endswith('}'):
                exp = exp[1:-1].strip()
            if exp == '2':
                return " squared"
            if exp == '3':
                return " cubed"
            return f" raised to the power {exp}"

        text = standalone_caret.sub(standalone_repl, text)

        # 3) Unicode superscripts after a base token
        sup_map = {
            '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
            '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
            '⁺': '+', '⁻': '-', '⁽': '(', '⁾': ')', 'ⁿ': 'n'
        }
        sup_chars = ''.join(map(re.escape, sup_map.keys()))
        superscript_pattern = re.compile(rf"(?P<base>[A-Za-z0-9_.()\[\]{{}}]+)(?P<sup>[{sup_chars}]+)")

        def superscript_repl(m: re.Match) -> str:
            base = m.group('base')
            sup_seq = m.group('sup')
            exp = ''.join(sup_map.get(ch, '') for ch in sup_seq)
            if exp == '2':
                return f"{base} squared"
            if exp == '3':
                return f"{base} cubed"
            if exp:
                return f"{base} raised to the power {exp}"
            return base

        text = superscript_pattern.sub(superscript_repl, text)

        # 4) Prefer saying "by" instead of "slash" for math-like X/Y patterns
        slash_pattern = re.compile(r"(?P<left>[A-Za-z0-9()\[\]{}]+)\s*/\s*(?P<right>[A-Za-z0-9()\[\]{}]+)")
        math_words = {"sin","cos","tan","log","ln","pi","theta","alpha","beta","gamma","delta","lambda","phi","psi","omega","sigma","mu","nu","eta","rho","xi","zeta","k","n","m","x","y","z"}

        def is_mathy(tok: str) -> bool:
            t = tok.lower()
            return (
                any(ch.isdigit() for ch in t)
                or len(t) <= 2
                or any(c in t for c in "()[]{}")
                or t in math_words
            )

        def slash_repl(m: re.Match) -> str:
            left = m.group('left')
            right = m.group('right')
            if is_mathy(left) or is_mathy(right):
                return f"{left} by {right}"
            return f"{left}/{right}"

        text = slash_pattern.sub(slash_repl, text)

        # 5) Convert binary '-' to 'minus' in math contexts; keep prose hyphens
        minus_pattern = re.compile(r"(?P<left>[A-Za-z0-9)\]\}]+)\s*-\s*(?P<right>[A-Za-z0-9(\[\{]+)")

        def minus_repl(m: re.Match) -> str:
            left = m.group('left')
            right = m.group('right')
            # keep numeric ranges as hyphen; later prose step turns to 'to'
            if left.isdigit() and right.isdigit():
                return f"{left}-{right}"
            if is_mathy(left) or is_mathy(right):
                return f"{left} minus {right}"
            return f"{left}-{right}"

        text = minus_pattern.sub(minus_repl, text)

        # 6) Unary minus before number/variable -> say 'minus X'
        unary_minus_pattern = re.compile(r"(^|[\s(=/+*^])-(?=\s*[A-Za-z0-9])")
        text = unary_minus_pattern.sub(lambda m: (" " if m.group(1).strip()=="" else m.group(1)) + "minus ", text)

        return text

    def is_active(self) -> bool:
        """Check if TTS is currently synthesizing or playing audio."""
        return (
            self.is_synthesizing or
            self.is_playing or
            not self.queue.empty() or
            bool(self.text_buffer)
        )

    def get_status(self) -> dict:
        """Get detailed TTS status information."""
        return {
            "is_synthesizing": self.is_synthesizing,
            "is_playing": self.is_playing,
            "queue_size": self.queue.qsize(),
            "buffer_size": len(self.text_buffer),
            "buffer_words": len(self.text_buffer.split()) if self.text_buffer else 0,
            "is_active": self.is_active()
        }

    def configure_buffering(self, min_words: int = 3, min_chars: int = 15, buffer_timeout: float = 1.5):
        """Configure the text buffering thresholds."""
        self.min_words = max(1, min_words)  # At least 1 word
        self.min_chars = max(5, min_chars)  # At least 5 characters
        self.buffer_timeout = max(0.5, buffer_timeout)  # At least 0.5 seconds
        print(f"[TTS] Buffering configured: min_words={self.min_words}, min_chars={self.min_chars}, timeout={self.buffer_timeout}s")

    def get_buffering_config(self) -> dict:
        """Get current buffering configuration."""
        return {
            "min_words": self.min_words,
            "min_chars": self.min_chars,
            "buffer_timeout": self.buffer_timeout
        }

    def _ensure_worker(self):
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())

    async def enqueue(self, ws: WebSocket, text: str):
        # ignore empty / whitespace only
        if not (text or "").strip():
            return
        # Clean text before buffering
        cleaned = self._clean_text(text)
        if not cleaned:
            return
        
        async with self.lock:
            # Cancel any pending buffer flush
            if self.buffer_flush_task and not self.buffer_flush_task.done():
                self.buffer_flush_task.cancel()
                self.buffer_flush_task = None
            
            # If this is a new WebSocket or buffer is empty, start fresh
            if self.buffer_ws != ws or not self.text_buffer:
                # Flush any existing buffer for different WebSocket
                if self.text_buffer and self.buffer_ws and self.buffer_ws != ws:
                    await self._flush_buffer()
                
                self.buffer_ws = ws
                self.text_buffer = ""
            
            # Add cleaned text to buffer
            if self.text_buffer:
                self.text_buffer += " " + cleaned
            else:
                self.text_buffer = cleaned
            
            self.last_chunk_time = asyncio.get_event_loop().time()
            
            # Check if buffer meets thresholds for immediate processing
            word_count = len(self.text_buffer.split())
            char_count = len(self.text_buffer)
            
            if word_count >= self.min_words or char_count >= self.min_chars:
                # Buffer is large enough, process immediately
                await self._flush_buffer()
            else:
                # Buffer is too small, schedule a delayed flush
                self.buffer_flush_task = asyncio.create_task(self._delayed_flush())
        
        self._ensure_worker()

    async def _flush_buffer(self):
        """Flush the current text buffer to the synthesis queue."""
        if self.text_buffer and self.buffer_ws:
            cleaned = self._clean_text(self.text_buffer)
            if cleaned:
                await self.queue.put((self.buffer_ws, cleaned))
            self.text_buffer = ""
            self.buffer_ws = None

    async def _delayed_flush(self):
        """Wait for timeout then flush buffer if no new chunks arrive."""
        try:
            await asyncio.sleep(self.buffer_timeout)
            async with self.lock:
                # Check if we still have the same content (no new chunks arrived)
                current_time = asyncio.get_event_loop().time()
                if (current_time - self.last_chunk_time) >= self.buffer_timeout:
                    await self._flush_buffer()
        except asyncio.CancelledError:
            # Flush was cancelled because new content arrived
            pass

    async def _worker(self):
        # Simple reliable sequential worker (prefetch removed for correctness)
        while True:
            ws, text = await self.queue.get()
            try:
                self.is_synthesizing = True
                await self._synthesize_one(ws, text)
            # except Exception as e:
            #     print(f"[TTS] worker error: {e}")
            finally:
                self.is_synthesizing = False
                self.queue.task_done()

    async def _synthesize_one(self, ws: WebSocket, text: str) -> None:
        """Stream one utterance using incremental ffmpeg decode to reduce CPU spikes/stutter.

        Falls back to legacy re-decode approach if ffmpeg is unavailable.
        """
        import shutil
        import struct

        self.current_cancel_event = asyncio.Event()
        voice = self.get_voice()
        communicate = edge_tts.Communicate(text, voice)
        self.streamer.is_raw_pcm = True

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            await self._synthesize_one_fallback(ws, text)
            return

        cmd = [
            ffmpeg_path,
            "-loglevel", "error",
            "-f", "mp3",
            "-i", "pipe:0",
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", str(self.streamer.target_channels),
            "-ar", str(self.streamer.target_rate),
            "pipe:1",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except NotImplementedError:
            # Event loop doesn't support subprocess (common on Windows with certain loops)
            await self._synthesize_one_fallback(ws, text)
            return
        except Exception as e:
            # Any other spawn error -> fallback to legacy streaming
            print(f"[TTS] ffmpeg spawn error: {e}. Falling back to legacy path.")
            await self._synthesize_one_fallback(ws, text)
            return

        # Only announce start once subprocess started successfully
        try:
            await ws.send_json({"type": "tts_start", "message": "TTS streaming started."})
        except Exception:
            pass

        leading_trim_applied = False
        silence_leadin_ms = 40
        silence_energy_threshold = 4
        initial_buffer = bytearray()
        min_start_buffer_ms = 30  # small jitter buffer
        min_start_samples = int((min_start_buffer_ms / 1000.0) * self.streamer.target_rate) * self.streamer.target_channels
        min_start_bytes = min_start_samples * 2
        READ_SIZE = 2048  # smaller read to reduce latency
        EMIT_CHUNK = 3072

        async def feed_mp3():
            try:
                async for part in communicate.stream():  # type: ignore[assignment]
                    if self.current_cancel_event.is_set():
                        break
                    if isinstance(part, dict) and part.get("type") == "audio":
                        data_part = part.get("data") or b""
                        if data_part and proc.stdin:
                            proc.stdin.write(data_part)
                            await proc.stdin.drain()
                    await asyncio.sleep(0)
            except Exception as e:
                print(f"[TTS] feed error: {e}")
            finally:
                if proc.stdin and not proc.stdin.is_closing():
                    try:
                        proc.stdin.close()
                    except Exception:
                        pass

        async def read_pcm():
            nonlocal leading_trim_applied
            try:
                while True:
                    if self.current_cancel_event.is_set():
                        break
                    if proc.stdout is None:
                        break
                    chunk = await proc.stdout.read(READ_SIZE)
                    if not chunk:
                        break
                    if not leading_trim_applied:
                        initial_buffer.extend(chunk)
                        if len(initial_buffer) < min_start_bytes:
                            continue
                        # Trim leading silence
                        sample_count = len(initial_buffer) // 2
                        max_trim_samples = int((silence_leadin_ms / 1000.0) * self.streamer.target_rate) * self.streamer.target_channels
                        trim_samples = 0
                        for i in range(min(sample_count, max_trim_samples)):
                            sample = struct.unpack_from('<h', initial_buffer, i * 2)[0]
                            if abs(sample) > silence_energy_threshold:
                                trim_samples = i
                                break
                        else:
                            trim_samples = min(sample_count, max_trim_samples)
                        pcm_to_write = initial_buffer[trim_samples*2:]
                        leading_trim_applied = True
                        for i in range(0, len(pcm_to_write), EMIT_CHUNK):
                            self.streamer.add_chunk(pcm_to_write[i:i+EMIT_CHUNK])
                    else:
                        self.streamer.add_chunk(chunk)
            except Exception as e:
                print(f"[TTS] read error: {e}")

        feeder = asyncio.create_task(feed_mp3())
        reader = asyncio.create_task(read_pcm())
        await asyncio.wait({feeder, reader}, return_when=asyncio.ALL_COMPLETED)
        try:
            await proc.wait()
        except Exception:
            pass

        if not self.current_cancel_event.is_set():
            try:
                await ws.send_json({"type": "tts_complete", "message": "TTS streaming completed."})
            except Exception:
                pass

    async def _synthesize_one_fallback(self, ws: WebSocket, text: str) -> None:
        """Legacy decode path kept as fallback (full re-decodes)."""
        self.current_cancel_event = asyncio.Event()
        voice = self.get_voice()
        communicate = edge_tts.Communicate(text, voice)
        self.streamer.is_raw_pcm = True
        mp3_accumulator = b""
        last_pcm_len = 0
        min_initial_bytes = 3000
        min_delta_bytes = 1800
        try:
            await ws.send_json({"type": "tts_start", "message": "TTS streaming started (fallback)."})
        except Exception:
            pass
        try:
            async for part in communicate.stream():  # type: ignore[assignment]
                if self.current_cancel_event.is_set():
                    break
                if isinstance(part, dict) and part.get("type") == "audio":
                    data_part = part.get("data") or b""
                    if data_part:
                        mp3_accumulator += data_part
                if len(mp3_accumulator) < min_initial_bytes and last_pcm_len == 0:
                    continue
                if len(mp3_accumulator) - last_pcm_len < min_delta_bytes:
                    continue
                try:
                    seg = AudioSegment.from_mp3(io.BytesIO(mp3_accumulator))
                    seg = seg.set_frame_rate(self.streamer.target_rate).set_channels(self.streamer.target_channels).set_sample_width(self.streamer.target_sample_width)
                    pcm = seg.raw_data
                    if len(pcm) > last_pcm_len:
                        delta = pcm[last_pcm_len:]
                        last_pcm_len = len(pcm)
                        for i in range(0, len(delta), 3072):
                            self.streamer.add_chunk(delta[i:i+3072])
                except Exception:
                    pass
        except Exception as e:
            print(f"[TTS] fallback synthesis error: {e}")
        # Final flush
        try:
            seg = AudioSegment.from_mp3(io.BytesIO(mp3_accumulator))
            seg = seg.set_frame_rate(self.streamer.target_rate).set_channels(self.streamer.target_channels).set_sample_width(self.streamer.target_sample_width)
            pcm = seg.raw_data
            if len(pcm) > last_pcm_len:
                delta = pcm[last_pcm_len:]
                for i in range(0, len(delta), 3072):
                    self.streamer.add_chunk(delta[i:i+3072])
        except Exception:
            pass
        if not self.current_cancel_event.is_set():
            try:
                await ws.send_json({"type": "tts_complete", "message": "TTS streaming completed (fallback)."})
            except Exception:
                pass


    def interrupt(self):
        # Cancel current utterance and clear pending queue contents
        self.current_cancel_event.set()
        
        # Cancel any pending buffer flush
        if self.buffer_flush_task and not self.buffer_flush_task.done():
            self.buffer_flush_task.cancel()
            self.buffer_flush_task = None
        
        # Clear text buffer
        self.text_buffer = ""
        self.buffer_ws = None
        
        # Clear the queue safely
        cleared_items = 0
        try:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                    cleared_items += 1
                except asyncio.queues.QueueEmpty:
                    break
        except Exception as e:
            print(f"[TTS] Error clearing queue: {e}")
        
        if cleared_items > 0:
            print(f"[TTS] Cleared {cleared_items} items from queue")
        
        # Reset status
        self.is_synthesizing = False
        self.is_playing = False
        
        self.streamer.stop()
        print("[TTS] TTS interrupted and stopped")

    def stop_all_sessions(self):  # compatibility for voice router if needed
        self.interrupt()


tts_manager = TTSManager()


async def synthesize_text(ws, text: str):
    """Public API: enqueue text for serialized TTS (non-blocking)."""
    print(f"[TTS] Enqueuing text for synthesis: {text[:30]}{'...' if len(text) > 30 else ''}")
    await tts_manager.enqueue(ws, text)


async def stop_tts():
    """Interrupt any ongoing and queued TTS playback."""
    tts_manager.interrupt()


def is_tts_active() -> bool:
    """Check if TTS is currently synthesizing or playing audio."""
    return tts_manager.is_active()


def get_tts_status() -> dict:
    """Get detailed TTS status information."""
    return tts_manager.get_status()


def configure_tts_buffering(min_words: int = 3, min_chars: int = 15, buffer_timeout: float = 1.5):
    """Configure TTS text buffering for short chunks."""
    tts_manager.configure_buffering(min_words, min_chars, buffer_timeout)


def get_tts_buffering_config() -> dict:
    """Get current TTS buffering configuration."""
    return tts_manager.get_buffering_config()

async def test():
    # chunks = [
    #     "Absolutely! Let's find those math chapters for you.\n\nAccording to the syllabus for Mathematics (11 MM-04), here are the chapters coming in Unit Test - I:\n\n*   **Sets**\n*   **Relations and Functions",
    #     "This is a test.",
    #     "How are you today?",
    #     "Long text, with multiple sentences. This should be handled correctly by the TTS system."
    # ]
    chunks = [
        "#Oh",
        " no! I can't believe it's already 2024-2025.",
        "Follow me at https://example.com/test?query=1-2 for more info.",
        "Here's a math equation: $E=mc^2$ and another one: $x^{n+1} = x^n * x$.",
        "(image) ![alt text](image_url) and some **bold text** with a link: [OpenAI](https://openai.com).",
    ]

    class FakeWS:
        async def send_json(self, data):
            print(f"[FakeWS] Sending JSON: {data}")

    ws = FakeWS()
    for chunk in chunks:
        asyncio.create_task(synthesize_text(ws, chunk))
        await asyncio.sleep(0.1)

    await asyncio.sleep(50)  # Let some TTS play

if __name__ == "__main__":
    asyncio.run(test())