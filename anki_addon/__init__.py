from aqt import mw
from aqt.qt import QAction, QKeySequence, QApplication
import os

from .log_util import log
from typing import Any

from .window_monitor import WindowMonitor
from .image_opener import ImageOpener
from .sound_player import SoundPlayer
from .unclosable_window import PersistentReviewWindow

# Initialize helper classes
_addon_dir = os.path.dirname(__file__)
image_opener = ImageOpener(_addon_dir)
sound_player = SoundPlayer(_addon_dir)
window_monitor = WindowMonitor()
log('addon initialized')
persistent_review_window = PersistentReviewWindow(mw)

from .window_monitor import WindowState
on_blacklisted_switch = lambda _, curr, __: image_opener.open_images() if curr == WindowState.BLACKLISTED else None

window_monitor.subscribe(on_blacklisted_switch)
window_monitor.subscribe(persistent_review_window.on_window_state_change)

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
def _on_focus_changed(old: Any, new: Any) -> None:
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
from typing import Any

app = QApplication.instance()
if app is not None:
    try:
        app.focusChanged.connect(_on_focus_changed)
    except Exception:
        # some bindings or environments may not expose the signal; ignore in that case
        pass

# Intercept Cmd+Q to prevent quitting when persistent window is active or during review
original_quit = mw.closeEvent

def _on_main_window_close_attempt(event):
    """Prevent closing Anki if persistent review window is active or during review session."""
    from aqt.qt import QTimer
    
    # Check if persistent review window is active
    if persistent_review_window.is_active:
        log("Cmd+Q blocked - persistent review window is active")
        event.ignore()
        persistent_review_window._bring_to_front()
        persistent_review_window.title_label.setText("⚠️ You cannot cheat your way out of this! Complete your reviews first!")
        return
    
    # Check if user is in review mode and hasn't completed enough reviews
    curr_reviews = persistent_review_window.get_reviews_today() - persistent_review_window._starting_reviews
    reviews_needed = persistent_review_window.REQUIRED_REVIEWS
    
    if mw.state == "review" and curr_reviews < reviews_needed:
        log(f"Cmd+Q blocked - user in review mode, {curr_reviews}/{reviews_needed} reviews done")
        event.ignore()
        # Show a warning notification
        from aqt.utils import showInfo
        showInfo(f"⚠️ You cannot cheat your way out of this! You need to complete {reviews_needed - curr_reviews} more reviews.")
        return
    
    # Otherwise, allow quitting
    original_quit(event)

mw.closeEvent = _on_main_window_close_attempt

# Start window monitoring
window_monitor.start()

# Additional shortcut: Alt+P to open the persistent review window
altp_action = QAction("Open Persistent Review Window (Alt+P)", mw)
altp_action.setShortcut(QKeySequence("Alt+P"))
altp_action.triggered.connect(persistent_review_window.start)
mw.form.menuTools.addAction(altp_action)

# Menu action to close persistent window (Alt+Shift+U)
close_unclosable_action = QAction("Close Persistent Review Window", mw)
close_unclosable_action.setShortcut(QKeySequence("Alt+O"))
close_unclosable_action.triggered.connect(persistent_review_window.stop)
mw.form.menuTools.addAction(close_unclosable_action)


