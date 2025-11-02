"""SoundPlayer - Handles audio playback in Anki."""

from aqt.utils import showInfo
from aqt.qt import QTimer
import os


from typing import Optional, Any

class SoundPlayer:
    """Handles playing sound files using Anki's sound system."""

    def __init__(self, addon_dir: str) -> None:
        """Initialize the SoundPlayer.
        Args:
            addon_dir: Directory path where the addon files are located
        """
        self.addon_dir: str = addon_dir
        self._sound_timer: Any = None

    def play_sound(self, audio_file: str = "a.mp3") -> None:
        """Play a sound file using Anki's sound API.
        Args:
            audio_file: Name of the audio file (relative to addon directory)
        """
        # Coerce QAction.triggered(bool) accidental arg
        if isinstance(audio_file, bool):
            audio_file = "a.mp3"

        audio_path: str = os.path.join(self.addon_dir, audio_file)
        if not os.path.exists(audio_path):
            showInfo(f"Sound not found: {audio_path}")
            return

        try:
            from aqt import sound
            # Expect Anki's `sound.play(path)` API
            sound.play(audio_path)
        except Exception:
            showInfo("Unable to play sound: `aqt.sound` not available or failed.")
    
    def start_spam(self, interval_ms: int = 3000, audio_file: str = "a.mp3") -> None:
        """Start continuously playing sound every interval_ms milliseconds.
        
        Args:
            interval_ms: How often to play sound (default 3000ms)
            audio_file: Audio file to play repeatedly
        """
        if self._sound_timer is None:
            self._sound_timer = QTimer()
            self._sound_timer.timeout.connect(lambda: self.play_sound(audio_file))
            self._sound_timer.start(interval_ms)
    
    def stop_spam(self) -> None:
        """Stop continuously playing sound."""
        if self._sound_timer is not None:
            self._sound_timer.stop()
            self._sound_timer = None
