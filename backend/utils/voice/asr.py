import asyncio
import sys
import sounddevice as sd
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from dotenv import load_dotenv
import time

load_dotenv()

# --- CONFIG ---
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 1024
MODEL = "nova-3"
# --------

# Create Deepgram client
dg = DeepgramClient()
connection = dg.listen.websocket.v("1")

# Async queue for audio chunks
audio_queue = asyncio.Queue()
# Keep a reference to the main event loop for thread-safe callbacks
MAIN_LOOP: asyncio.AbstractEventLoop | None = None


transcript_result = ""

def on_open(self, open, **kwargs):
    print(f"\n\n{open}\n\n")


def on_message(self, result, **kwargs):
    sentence = result.channel.alternatives[0].transcript
    if len(sentence) == 0:
        return
    if result.is_final:
        print(f"final: {sentence}")
        global transcript_result
        transcript_result += str(sentence) + " "
    print(f"speaker: {sentence}")


def on_metadata(self, metadata, **kwargs):
    print(f"\n\n{metadata}\n\n")


def on_speech_started(self, speech_started, **kwargs):
    print(f"\n\n{speech_started}\n\n")


def on_utterance_end(self, utterance_end, **kwargs):
    global transcript_result
    print(f"\n\n{utterance_end}\n\n")
    print(f"Full transcription so far: {transcript_result}")
    transcript_result = ""  # Clear after printing


def on_close(self, close, **kwargs):
    print(f"\n\n{close}\n\n")


def on_error(self, error, **kwargs):
    print(f"\n\n{error}\n\n")


def on_unhandled(self, unhandled, **kwargs):
    print(f"\n\n{unhandled}\n\n")


def on_finalize(self, finalize, **kwargs):
    print(f"\n\n{finalize}\n\n")


connection.on(LiveTranscriptionEvents.Open, on_open)
connection.on(LiveTranscriptionEvents.Transcript, on_message)
connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
# connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
connection.on(LiveTranscriptionEvents.Close, on_close)
connection.on(LiveTranscriptionEvents.Error, on_error)
connection.on(LiveTranscriptionEvents.Unhandled, on_unhandled)
connection.on(LiveTranscriptionEvents.Finalize, on_finalize)

options = LiveOptions(
    model=MODEL,
    encoding="linear16",
    sample_rate=SAMPLE_RATE,
    smart_format=True,
    vad_events=True,
    interim_results=True,
    utterance_end_ms="1000",
    language="multi",  # or specify a language code like "en-US"
)

additional_options = {
    "mip_opt_out": True  # Provide 50% discount and opt out of data collection
}




# Audio callback → push to asyncio queue
def audio_callback(indata, frames, time, status):
    if status:
        print("Audio status:", status, file=sys.stderr)
    data = bytes(indata)
    # Use the main loop captured in main() because this callback runs in a different thread
    if MAIN_LOOP is not None:
        MAIN_LOOP.call_soon_threadsafe(audio_queue.put_nowait, data)
    else:
        # Drop data until loop is ready (very short window during startup)
        pass


async def microphone_sender():
    """Coroutine that takes audio from the queue and sends to Deepgram"""
    while True:
        chunk = await audio_queue.get()
        connection.send(chunk)


async def main():
    # Capture the running event loop for use in the audio callback thread
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()

    # input("Press Enter to connect to deepgragm...")
    t = time.time()
    connection.start(options, additional_options)
    print("Deepgram websocket connected in ", time.time() - t, "seconds")

    # Start microphone stream
    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCKSIZE,
        dtype="int16",
        channels=CHANNELS,
        callback=audio_callback,
    )
    stream.start()

    print("Recording... press Ctrl+C to stop.")
    try:
        await microphone_sender()
    except asyncio.CancelledError:
        pass
    finally:
        stream.stop()
        stream.close()
        connection.finish()
        print("Connection closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
