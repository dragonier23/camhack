"""ImageOpener - Manages spawning and closing image windows in Anki."""

from aqt.qt import QLabel, QPixmap, QWidget, QVBoxLayout, Qt, QApplication, QPushButton
from aqt.utils import showInfo
from aqt import mw
import os
import random


from typing import List, Any, Tuple

class ImageOpener:
    """Handles opening and closing image windows at random screen positions."""
    MAX_WINDOWS: int = 100  # Hard limit on number of windows

    def __init__(self, addon_dir: str) -> None:
        """Initialize the ImageOpener.
        Args:
            addon_dir: Directory path where the addon files are located
        """
        self.addon_dir: str = addon_dir
        self._image_windows: List[Any] = []

    def open_images(self, input_file: str = "a.png", spawn_count: int = 5) -> None:
        """Open a small, safe number of windows showing an image.
        Each window is placed at a random location on the user's screen.
        Args:
            input_file: Name of the image file (relative to addon directory)
            spawn_count: Number of windows to spawn
        """
        # Enforce hard limit on total windows
        current_count: int = len(self._image_windows)
        if current_count >= self.MAX_WINDOWS:
            return

        # Adjust spawn_count if it would exceed the limit
        available_slots: int = self.MAX_WINDOWS - current_count
        spawn_count = min(spawn_count, available_slots)

        if spawn_count <= 0:
            return

        image_path: str = os.path.join(self.addon_dir, input_file)
        if not os.path.exists(image_path):
            showInfo(f"Image not found: {image_path}")
            return

        for i in range(spawn_count):
            w = QWidget()
            # Make window stay on top of other windows
            w.setWindowFlags(w.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            w.setWindowTitle(f"Anki {i+1}")
            layout = QVBoxLayout(w)
            label = QLabel()
            pix = QPixmap(image_path)
            if pix.isNull():
                showInfo("Failed to load image (invalid image file).")
                return

            # Limit the displayed image to max width=200 and max height=300 while keeping aspect ratio
            max_w, max_h = 200, 300
            scaled_pix = pix.scaled(max_w, max_h)
            label.setPixmap(scaled_pix)
            layout.addWidget(label)

            # Add button to switch back to Anki
            back_button = QPushButton("Back to Anki")
            back_button.clicked.connect(self._switch_to_anki)
            layout.addWidget(back_button)

            w.setLayout(layout)
            # Size the window to the scaled image
            w.resize(scaled_pix.width(), scaled_pix.height())

            # Compute a random position on the user's screen (supports multi-monitor setups)
            x, y = self._get_random_position(w)
            w.move(x, y)
            w.show()
            self._image_windows.append(w)
    
    def _get_random_position(self, widget):
        """Calculate a random position for a widget on the screen.
        
        Args:
            widget: The QWidget to position
            
        Returns:
            Tuple of (x, y) coordinates
        """
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                raise RuntimeError("no primary screen")
            geom = screen.availableGeometry()
            x_min = geom.x()
            y_min = geom.y()
            x_max = geom.x() + max(0, geom.width() - widget.width())
            y_max = geom.y() + max(0, geom.height() - widget.height())

            if x_max < x_min:
                x = x_min
            else:
                x = random.randint(x_min, x_max)

            if y_max < y_min:
                y = y_min
            else:
                y = random.randint(y_min, y_max)
        except Exception:
            # Fallback if screen geometry isn't available: use a safe random offset
            x = 100 + random.randint(0, 300)
            y = 100 + random.randint(0, 300)
        
        return x, y
    
    def _switch_to_anki(self):
        """Activate and bring Anki main window to the front."""
        try:
            if mw is not None:
                mw.activateWindow()
                mw.raise_()
        except Exception:
            # best-effort; ignore errors
            pass
    
    def close_images(self):
        """Close all image windows opened by this instance."""
        while self._image_windows:
            w = self._image_windows.pop()
            try:
                w.close()
            except Exception:
                # best-effort close; ignore errors
                pass
