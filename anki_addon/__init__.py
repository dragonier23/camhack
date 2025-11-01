from aqt import mw
from aqt.qt import QAction, QKeySequence, QApplication
import os

from .window_monitor import WindowMonitor
from .image_opener import ImageOpener
from .sound_player import SoundPlayer

# Initialize helper classes
_addon_dir = os.path.dirname(__file__)
image_opener = ImageOpener(_addon_dir)
sound_player = SoundPlayer(_addon_dir)
window_monitor = WindowMonitor(on_blacklisted_switch=image_opener.open_images)


# Menu actions: open on Alt+C
open_action = QAction("Open Images", mw)
open_action.setShortcut(QKeySequence("Alt+C"))
open_action.triggered.connect(image_opener.open_images)
mw.form.menuTools.addAction(open_action)

# Play sound action (Alt+B) — use only aqt.sound as requested
play_action = QAction("Play Sound", mw)
play_action.setShortcut(QKeySequence("Alt+B"))
play_action.triggered.connect(sound_player.play_sound)
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
            image_opener.close_images()
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

# Start window monitoring
window_monitor.start()

# Additional shortcut: Alt+P to open the persistent review window
altp_action = QAction("Open Persistent Review Window (Alt+P)", mw)
altp_action.setShortcut(QKeySequence("Alt+P"))
altp_action.triggered.connect(unclosable_window.open_unclosable_window)
mw.form.menuTools.addAction(altp_action)

# Menu action to close persistent window (Alt+Shift+U)
close_unclosable_action = QAction("Close Persistent Review Window", mw)
close_unclosable_action.setShortcut(QKeySequence("Alt+Shift+U"))
close_unclosable_action.triggered.connect(unclosable_window.close_unclosable_window)
mw.form.menuTools.addAction(close_unclosable_action)
