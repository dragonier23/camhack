"""ImageOpener - Manages spawning and closing image windows in Anki."""

import os
import random
from typing import Any, List, Tuple

from aqt import mw
from aqt.qt import (QApplication, QCloseEvent, QEvent, QLabel, QObject, QPixmap,
                    QPushButton, Qt, QTimer, QVBoxLayout, QWidget)
from aqt.utils import showInfo

from .log_util import log
from .window_monitor import WindowState


class ImageOpener:
    """Handles opening and closing image windows at random screen positions."""
    MAX_WINDOWS: int = 5  # Hard limit on number of windows

    def __init__(self, addon_dir: str) -> None:
        """Initialize the ImageOpener.
        Args:
            addon_dir: Directory path where the addon files are located
        """
        self.addon_dir: str = addon_dir
        self._image_windows: List[Any] = []
        self._open_timer: Any = None
        self._randomise_timer: Any = None

    def open_images(self, spawn_count: int = 1) -> None:
        """Open a small, safe number of windows showing an image.
        Each window is placed at a random location on the user's screen.
        Args:
            input_file: Name of the image file (relative to addon directory)
            spawn_count: Number of windows to spawn
        """

        input_file = random.choice(["a.png", "churchill.jpeg", "concerned.jpeg", "confused.jpeg", "happy.jpeg", "inquisitive.jpeg", "john.jpeg", "judging.jpeg", "looking.jpeg", "smiling.jpeg"])

        # Enforce hard limit on total windows
        current_count: int = len(self._image_windows)
        log(f'{current_count}/{self.MAX_WINDOWS} windows open!')
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
            w.setWindowTitle("COME BACK TO ANKI!!")
            
            # Install event filter to detect focus events
            w.installEventFilter(self._create_focus_filter(w))
            
            layout = QVBoxLayout(w)
            label = QLabel()
            pix = QPixmap(image_path)
            if pix.isNull():
                showInfo("Failed to load image (invalid image file).")
                return

            # Limit the displayed image to max width=200 and max height=300 while keeping aspect ratio
            max_w, max_h = 200, 300
            scaled_pix = pix.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled_pix)
            layout.addWidget(label)

            # Add text label
            text_label = QLabel("COME BACK TO ANKI!!")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(text_label)

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
    
    def _create_focus_filter(self, widget):
        """Create an event filter that detects mouse press and close events on the widget.
        
        Args:
            widget: The widget to monitor for mouse presses and close events
            
        Returns:
            Event filter object
        """
        class FocusEventFilter(QObject):
            def __init__(self, parent_opener, window):
                super().__init__(mw)
                self.parent_opener = parent_opener
                self.window = window
            
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.MouseButtonPress:
                    # Window was clicked - switch to Anki and close all windows
                    self.parent_opener._switch_to_anki()
                    self.parent_opener.close_images()
                    self.parent_opener.stop_spam()
                    return True
                return False
        
        return FocusEventFilter(self, widget)
    
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
    
    def _randomise_positions(self) -> None:
        """Randomize the positions of all open windows by closing and respawning them."""
        # Clean up any windows that have been closed
        self._image_windows = [w for w in self._image_windows if w.isVisible()]
        
        # Get the current count of visible windows
        current_count = len(self._image_windows)
        
        # Close all current windows
        self.close_images()
        
        # Spawn them again at new random positions
        if current_count > 0:
            self.open_images(spawn_count=current_count)
    
    def start_spam(self, interval_ms: int = 1000 * 3) -> None:
        """Start continuously spawning images every interval_ms milliseconds.
        
        Args:
            interval_ms: How often to spawn images (default 500ms)
        """
        self._image_windows = []
        if self._open_timer is None:
            log('starting spam')
            self._open_timer = QTimer()
            self._open_timer.timeout.connect(self.open_images)
            self._open_timer.start(interval_ms)
        
        # Start randomizing positions every 2 seconds
        if self._randomise_timer is None:
            self._randomise_timer = QTimer()
            self._randomise_timer.timeout.connect(self._randomise_positions)
            self._randomise_timer.start(4000)
    
    def stop_spam(self) -> None:
        """Stop continuously spawning images."""
        if self._open_timer is not None:
            self._open_timer.stop()
            self._open_timer = None
        if self._randomise_timer is not None:
            self._randomise_timer.stop()
            self._randomise_timer = None
    
    def on_window_state_change(self, prev_state: WindowState, curr_state: WindowState, curr_title: str) -> None:
        """Handle changes in the window state."""
        if curr_state == WindowState.UNCLASSIFIED:
            self.start_spam()
        else:
            self.stop_spam()