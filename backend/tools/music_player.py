# Not Working now, need to fix later

from yt_dlp import YoutubeDL

import vlc
import threading
import time
from agno.tools import Toolkit
from agno.agent import Agent


class SongPlayer:
    def __init__(self):
        self.player = None
        self.lock = threading.Lock()
        self.current_url = None
        self.status_thread = None
        self.running = False

    def _start_status_thread(self):
        if not self.status_thread or not self.status_thread.is_alive():
            self.running = True
            self.status_thread = threading.Thread(target=self._status_updater, daemon=True)
            self.status_thread.start()

    def _status_updater(self):
        while self.running:
            time.sleep(1)
            with self.lock:
                if self.player:
                    if self.player.get_state() == vlc.State.Ended:
                        self.stop()
                        break

    def play(self, url):
        with self.lock:
            if self.player:
                self.player.stop()
                self.player.release()
            self.player = vlc.MediaPlayer(url)
            self.player.play()
            self.current_url = url
            self._start_status_thread()

    def pause(self):
        with self.lock:
            if self.player:
                self.player.pause()

    def stop(self):
        with self.lock:
            if self.player:
                self.player.stop()
                self.player.release()
                self.player = None
            self.current_url = None
            self.running = False

    def is_playing(self):
        with self.lock:
            return self.player and self.player.is_playing()

    def _get_state_string(self, state):
        """Convert VLC state to string representation"""
        state_map = {
            vlc.State.NothingSpecial: "idle",
            vlc.State.Opening: "opening",
            vlc.State.Buffering: "buffering", 
            vlc.State.Playing: "playing",
            vlc.State.Paused: "paused",
            vlc.State.Stopped: "stopped",
            vlc.State.Ended: "ended",
            vlc.State.Error: "error"
        }
        return state_map.get(state, "unknown")

    def get_status(self):
        with self.lock:
            if not self.player:
                return {"status": "stopped"}

            state = self.player.get_state()
            played_ms = self.player.get_time()
            total_ms = self.player.get_length()
            progress = 0.0

            if total_ms > 0:
                progress = (played_ms / total_ms) * 100

            print(f"State: {state}, Played: {played_ms}ms, Total: {total_ms}ms, Progress: {progress}%")

            return {
                "status": self._get_state_string(state),
                "played": self._format_time(played_ms),
                "total": self._format_time(total_ms),
                "progress": round(progress, 2)
            }

    def _format_time(self, ms):
        if ms <= 0:
            return "0:00"
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{int(minutes)}:{int(seconds):02}"


class MusicPlayerToolkit(Toolkit):
    def __init__(self, **kwargs):
        super().__init__(name="music_player", tools=[
            self.play_song,
            self.pause_song,
            self.resume_song,
            self.stop_song,
            self.get_song_status
        ], **kwargs)
        self.player = SongPlayer()
        self.current_song_title = None

    def play_song(self, query: str) -> str:
        """
        Plays a song from a given search query (e.g., from YouTube).

        Args:
            query (str): The search query for the song.

        Returns:
            str: A message indicating the song is playing and its title.
        """
        try:
            url, title = get_audio_stream_url(query)
            self.current_song_title = title
            # The player runs in a separate thread to not block the agent
            threading.Thread(target=self.player.play, args=(url,), daemon=True).start()
            return f"🎵 Playing: {title}"
        except Exception as e:
            return f"❌ Error finding or playing song: {e}"

    def pause_song(self) -> str:
        """Pauses the currently playing song."""
        self.player.pause()
        return "⏸️ Song paused."

    def resume_song(self) -> str:
        """Resumes the currently paused song."""
        self.player.pause()  # VLC's pause method toggles play/pause
        return "▶️ Song resumed."

    def stop_song(self) -> str:
        """Stops the currently playing song and clears its state."""
        self.player.stop()
        self.current_song_title = None
        return "🛑 Song stopped."

    def get_song_status(self) -> str:
        """Gets the status of the current song, including progress and title."""
        status = self.player.get_status()
        if status['status'] in ["stopped", "ended", "error", "idle"]:
            return f"No song is currently playing. Status: {status['status'].capitalize()}"

        title_str = f"({self.current_song_title}) " if self.current_song_title else ""
        return f"Status: {status['status'].capitalize()} {title_str}- {status['played']} / {status['total']} ({status['progress']}%)"


def get_audio_stream_url(query: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch1',  # get only top result
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        video = info['entries'][0] if 'entries' in info else info
        return video['url'], video['title']


# Example usage
if __name__ == "__main__":
    # To use this toolkit, you would typically initialize an Agent like this:
    agent = Agent(tools=[MusicPlayerToolkit()], show_tool_calls=True, markdown=True)

    print("🎵 Gravia Music Agent Ready 🎵")
    print("Try commands like: 'play never gonna give you up', 'pause', 'status', 'stop', or 'exit'")
    while True:
        try:
            prompt = input("> ")
            if prompt.lower() == "exit":
                # Ensure the player is stopped before exiting
                agent.run("stop the song")
                print("👋 Exiting Gravia Music Agent.")
                break
            agent.print_response(prompt)
        except (KeyboardInterrupt, EOFError):
            agent.run("stop the song")
            print("\n👋 Exiting Gravia Music Agent.")
            break