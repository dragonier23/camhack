from aqt import mw
from aqt.qt import QAction, QKeySequence, QLabel, QPixmap, QWidget, QVBoxLayout, Qt, QApplication, QTimer
from aqt.utils import showInfo
import os
import random

from .window_monitor import get_active_window_info

# Keep references to the windows so they are not garbage-collected
_image_windows = []

def open_images(*args, input_file: str = "a.png", spawn_count: int = 5):
    """Open a small, safe number of windows showing `a.png` located next to this file.
    Each window is placed at a random location on the user's screen.
    """
    image_path = os.path.join(os.path.dirname(__file__), input_file)
    if not os.path.exists(image_path):
        showInfo(f"Image not found: {image_path}")
        return

    # Limit the number of windows to a reasonable value.
    spawn_count = spawn_count
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
        # scaled_pix = pix.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        scaled_pix = pix.scaled(max_w, max_h)
        label.setPixmap(scaled_pix)
        layout.addWidget(label)
        w.setLayout(layout)
        # Size the window to the scaled image
        w.resize(scaled_pix.width(), scaled_pix.height())

        # Compute a random position on the user's screen (supports multi-monitor setups)
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                raise RuntimeError("no primary screen")
            geom = screen.availableGeometry()
            x_min = geom.x()
            y_min = geom.y()
            x_max = geom.x() + max(0, geom.width() - w.width())
            y_max = geom.y() + max(0, geom.height() - w.height())

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

        w.move(x, y)
        w.show()
        _image_windows.append(w)


def close_images():
    """Close all image windows opened by this add-on."""
    while _image_windows:
        w = _image_windows.pop()
        try:
            w.close()
        except Exception:
            # best-effort close; ignore errors
            pass


# Menu actions: open on Alt+C
open_action = QAction("Open Images", mw)
open_action.setShortcut(QKeySequence("Alt+C"))
open_action.triggered.connect(open_images)
mw.form.menuTools.addAction(open_action)

# Play sound action (Alt+B) — use only aqt.sound as requested
def play_sound():
    audio_path = os.path.join(os.path.dirname(__file__), "a.mp3")
    if not os.path.exists(audio_path):
        showInfo(f"Sound not found: {audio_path}")
        return

    try:
        from aqt import sound
        # Expect Anki's `sound.play(path)` API
        sound.play(audio_path)
    except Exception:
        showInfo("Unable to play sound: `aqt.sound` not available or failed.")


play_action = QAction("Play Sound", mw)
play_action.setShortcut(QKeySequence("Alt+B"))
play_action.triggered.connect(play_sound)
mw.form.menuTools.addAction(play_action)

# Instead of a keyboard shortcut to close images, close them when the main Anki
# window receives focus again. Use QApplication.focusChanged to detect focus shifts.
def _on_focus_changed(old, new):
    try:
        if new is None:
            return
        # new.window() is the top-level window the newly focused widget belongs to
        top = new.window()
        if top is mw:
            close_images()
    except Exception:
        # best-effort; ignore errors
        pass

app = QApplication.instance()
if app is not None:
    try:
        app.focusChanged.connect(_on_focus_changed)
    except Exception:
        # some bindings or environments may not expose the signal; ignore in that case
        pass


# Window monitoring: detect when user switches to a non-Anki window
_previous_window_handle = None
_monitor_timer = None

def _check_window_change():
    """Called periodically to check if the active window changed to something outside Anki."""
    global _previous_window_handle
    try:
        current = get_active_window_info()
        current_handle = current.get('handle')
        
        # Check if window changed
        if _previous_window_handle is not None and current_handle != _previous_window_handle:
            # Window changed - check if it's NOT Anki
            title = current.get('title', '').lower()
            # Anki's process is typically 'anki.exe' on Windows
            if 'anki' not in title:
                open_images()
        
        _previous_window_handle = current_handle
    except Exception as e:
        # Silent fail - don't interrupt Anki's operation
        pass

# Initialize the monitor
try:
    initial_window = get_active_window_info()
    _previous_window_handle = initial_window.get('handle')
    
    # Create a timer that checks every 500ms
    _monitor_timer = QTimer()
    _monitor_timer.timeout.connect(_check_window_change)
    _monitor_timer.start(500)  # Check every 500ms
except Exception:
    # If initialization fails, just don't start monitoring
    pass

