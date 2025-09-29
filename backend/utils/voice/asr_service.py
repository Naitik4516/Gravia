import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable, Any, Dict

from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
import numpy as np
from config import DEEPGRAM_API_KEY

try:
    import onnxruntime as ort  # type: ignore
    silero_available = True
except Exception:  # pragma: no cover - optional dependency
    ort = None  # type: ignore
    silero_available = False

try:
    import sounddevice as sd
except ImportError:
    sd = None


@dataclass
class TranscriptionEvent:
    type: str  # 'partial' | 'final' | 'error' | 'status'
    text: str = ""
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] | None = None


class MicrophoneStream:
    def __init__(self, sample_rate: int, on_audio: Callable[[bytes], None]):
        if sd is None:
            raise ImportError(
                "sounddevice is not installed. Please install it to use server-side microphone."
            )
        self._sample_rate = sample_rate
        self._on_audio = on_audio
        self._stream = None

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")
        self._on_audio(bytes(indata))

    def start(self):
        if self._stream is not None:
            return
        self._stream = sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=1024,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None


class ASRSession:
    def __init__(
        self,
        deepgram: DeepgramClient,
        model: str,
        sample_rate: int,
        vad_timeout: float = 10.0,
        on_event: Optional[Callable[[TranscriptionEvent], Awaitable[None]]] = None,
        vad_session: Any | None = None,
        vad_threshold: float = 0.5,
    ):
        self._deepgram = deepgram
        self._connection = self._deepgram.listen.websocket.v("1")
        self._model = model
        self._sample_rate = sample_rate
        self._on_event = on_event
        self._started = False
        self._closed = False
        self._last_speech_time = time.time()
        self._vad_timeout = vad_timeout
        self._monitor_task: Optional[asyncio.Task] = None
        self._final_buffer: list[str] = []
        self._vad_session = vad_session
        self._vad_threshold = vad_threshold
        self._mic_stream: MicrophoneStream | None = None
        self._loop = None  # Store the event loop

        self._connection.on(LiveTranscriptionEvents.Open, self._on_open)
        self._connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
        self._connection.on(LiveTranscriptionEvents.Error, self._on_error)
        self._connection.on(LiveTranscriptionEvents.Close, self._on_close)
        self._connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end)

    async def start(self):
        if self._started:
            return
        self._started = True
        self._loop = asyncio.get_running_loop()  # Capture the main event loop

        # Start microphone capture
        self._mic_stream = MicrophoneStream(
            sample_rate=self._sample_rate, on_audio=self.send_audio
        )
        self._mic_stream.start()

        options = LiveOptions(
            model=self._model,
            encoding="linear16",
            sample_rate=self._sample_rate,
            interim_results=True,
            vad_events=True,
            utterance_end_ms="1000",
            smart_format=True,
        )
        self._connection.start(options, {"mip_opt_out": True})
        self._monitor_task = asyncio.create_task(self._monitor_vad())
        if self._on_event:
            await self._on_event(TranscriptionEvent(type="status", text="listening_started"))

    async def close(self):
        if self._closed:
            return
        self._closed = True

        if self._mic_stream:
            self._mic_stream.stop()
            self._mic_stream = None

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        try:
            self._connection.finish()
        except Exception:
            pass
        if self._on_event:
            await self._on_event(TranscriptionEvent(type="status", text="listening_stopped"))

    def send_audio(self, pcm16: bytes):
        # Optional local VAD (Silero) to refine inactivity timeout
        if self._vad_session and not self._closed and len(pcm16) >= 320:  # ~10ms
            try:
                audio = np.frombuffer(pcm16, dtype=np.int16).astype("float32") / 32768.0
                # Log the audio characteristics
                is_silent = np.all(audio == 0)
                max_abs_val = np.max(np.abs(audio))
                print(f"[VAD] Audio received - Silent: {is_silent}, Max abs value: {max_abs_val:.4f}")

                audio = audio.reshape(1, -1)
                sr_arr = np.array([self._sample_rate], dtype=np.int64)
                # The Silero ONNX model exported commonly uses input names 'input' and 'sr'
                ort_inputs = {"input": audio, "sr": sr_arr}
                prob = self._vad_session.run(None, ort_inputs)[0].squeeze()
                if float(prob) > self._vad_threshold:
                    self._last_speech_time = time.time()
            except Exception:  # pragma: no cover - best effort VAD
                pass
        if not self._closed:
            try:
                self._connection.send(pcm16)
            except Exception:  # pragma: no cover
                pass

    async def _monitor_vad(self):
        # Periodically check for inactivity
        try:
            while not self._closed:
                await asyncio.sleep(1.0)
                if time.time() - self._last_speech_time > self._vad_timeout:
                    if self._on_event:
                        await self._on_event(TranscriptionEvent(type="status", text="no_speech_timeout"))
                    await self.close()
                    break
        except asyncio.CancelledError:
            pass

    # Deepgram callbacks (sync) -> dispatch into loop
    def _on_open(self, *_):
        self._last_speech_time = time.time()

    def _dispatch_event(self, event: TranscriptionEvent):
        if self._on_event is None:
            return
        try:
            loop = self._loop or asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._on_event(event), loop)
            else:
                # fallback: just call directly (should not happen in prod)
                asyncio.create_task(self._on_event(event))
        except Exception as e:
            print(f"[ASRSession] Failed to dispatch event: {e}")

    def _on_transcript(self, _self, result, **_):
        try:
            alt = result.channel.alternatives[0]
            text = alt.transcript
            if not text:
                return
            if result.is_final:
                self._final_buffer.append(text)
                self._last_speech_time = time.time()
                ev = TranscriptionEvent(type="final", text=text)
            else:
                ev = TranscriptionEvent(type="partial", text=text)
            self._dispatch_event(ev)
        except Exception:
            pass

    def _on_utterance_end(self, *_args, **_kwargs):
        # Emit aggregated final if buffered segments exist
        if self._final_buffer and self._on_event:
            joined = " ".join(self._final_buffer).strip()
            self._final_buffer.clear()
            self._dispatch_event(TranscriptionEvent(type="final", text=joined))

    def _on_error(self, _self, error, **_):
        self._dispatch_event(TranscriptionEvent(type="error", text=str(error)))

    def _on_close(self, *_):
        if self._on_event and not self._closed:
            self._dispatch_event(TranscriptionEvent(type="status", text="connection_closed"))


class ASRManager:
    def __init__(self):
        self._deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        self._sessions: dict[str, ASRSession] = {}
        self._vad_session = None
        if silero_available:
            # Lazy load ONNX model; ignore failures
            try:
                self._vad_session = ort.InferenceSession("silero_vad.onnx", providers=["CPUExecutionProvider"])  # type: ignore
            except Exception:  # pragma: no cover
                self._vad_session = None

    async def start_session(
        self,
        session_key: str,
        model: str = "nova-3",
        sample_rate: int = 16000,
        vad_timeout: float = 10.0,
        on_event: Optional[Callable[[TranscriptionEvent], Awaitable[None]]] = None,
    ) -> ASRSession:
        existing = self._sessions.get(session_key)
        if existing:
            return existing
        session = ASRSession(
            deepgram=self._deepgram,
            model=model,
            sample_rate=sample_rate,
            vad_timeout=vad_timeout,
            on_event=on_event,
            vad_session=self._vad_session,
        )
        self._sessions[session_key] = session
        await session.start()
        return session

    def get(self, session_key: str) -> Optional[ASRSession]:
        return self._sessions.get(session_key)

    async def close_session(self, session_key: str):
        session = self._sessions.pop(session_key, None)
        if session:
            await session.close()

    async def close_all(self):
        keys = list(self._sessions.keys())
        for k in keys:
            await self.close_session(k)


# Singleton manager
asr_manager = ASRManager()
