from aqt import mw
from aqt.qt import QAction, QKeySequence, QLabel, QPixmap, QWidget, QVBoxLayout, Qt, QApplication
from aqt.utils import showInfo
import os
import random

# Keep references to the windows so they are not garbage-collected
_image_windows = []

def open_images():
    """Open a small, safe number of windows showing `a.png` located next to this file.
    Each window is placed at a random location within (or near) the Anki main window.
    """
    image_path = os.path.join(os.path.dirname(__file__), "a.png")
    if not os.path.exists(image_path):
        showInfo(f"Image not found: {image_path}")
        return

    # Limit the number of windows to a reasonable value.
    spawn_count = 50
    for i in range(spawn_count):
        w = QWidget()
        w.setWindowTitle(f"Image {i+1}")
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


# Menu actions: open on Alt+C, close on Alt+B
open_action = QAction("Open Images", mw)
open_action.setShortcut(QKeySequence("Alt+C"))
open_action.triggered.connect(open_images)
mw.form.menuTools.addAction(open_action)

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
