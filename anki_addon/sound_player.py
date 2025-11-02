"""SoundPlayer - Handles audio playback in Anki."""

from aqt.utils import showInfo
import os


from typing import Optional

class SoundPlayer:
    """Handles playing sound files using Anki's sound system."""

    def __init__(self, addon_dir: str) -> None:
        """Initialize the SoundPlayer.
        Args:
            addon_dir: Directory path where the addon files are located
        """
        self.addon_dir: str = addon_dir

    def play_sound(self, audio_file: str = "a.mp3") -> None:
        """Play a sound file using Anki's sound API.
        Args:
            audio_file: Name of the audio file (relative to addon directory)
        """
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
