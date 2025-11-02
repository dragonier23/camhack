from aqt import mw
from aqt.qt import QAction, QKeySequence, QApplication
import os

from .log_util import log
from typing import Any

from .window_monitor import WindowMonitor
from .image_opener import ImageOpener
from .sound_player import SoundPlayer
from .unclosable_window import PersistentReviewWindow
from .vision import EyeMonitor

# Initialize helper classes
_addon_dir = os.path.dirname(__file__)
image_opener = ImageOpener(os.path.join(_addon_dir, "assets", "images"))
sound_player = SoundPlayer(os.path.join(_addon_dir, "assets", "audio"))
window_monitor = WindowMonitor()
eye_monitor = EyeMonitor(addon_dir="C:/Users/user/Documents/GitHub/camhack/anki_addon", threshold_seconds=2.0)
log('addon initialized')
persistent_review_window = PersistentReviewWindow(mw)

window_monitor.subscribe(image_opener.on_window_state_change)
window_monitor.subscribe(persistent_review_window.on_window_state_change)

# Subscribe to eye monitor: start/stop sound spam based on eye state
def on_eye_state_change(eyes_closed: bool) -> None:
    """Handle eye state changes - spam sound when eyes closed too long."""
    if eyes_closed:
        log("Eyes closed for 2+ seconds - starting sound spam")
        sound_player.start_spam()
    else:
        log("Eyes opened - stopping sound spam")
        sound_player.stop_spam()

eye_monitor.subscribe(on_eye_state_change)

# Menu actions: open on Alt+C
open_action = QAction("Open Images", mw)
open_action.setShortcut(QKeySequence("Alt+C"))
open_action.triggered.connect(lambda checked=False: image_opener.open_images())
mw.form.menuTools.addAction(open_action)

# Start sound spam action (Alt+B)
start_sound_action = QAction("Start Sound Loop", mw)
start_sound_action.setShortcut(QKeySequence("Alt+B"))
start_sound_action.triggered.connect(lambda checked=False: sound_player.start_spam())
mw.form.menuTools.addAction(start_sound_action)

# Stop sound spam action (Alt+N)
stop_sound_action = QAction("Stop Sound Loop", mw)
stop_sound_action.setShortcut(QKeySequence("Alt+N"))
stop_sound_action.triggered.connect(lambda checked=False: sound_player.stop_spam())
mw.form.menuTools.addAction(stop_sound_action)

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

# Start eye monitoring
eye_monitor.start()

# Additional shortcut: Alt+P to open the persistent review window
altp_action = QAction("Open Persistent Review Window (Alt+P)", mw)
altp_action.setShortcut(QKeySequence("Alt+P"))
altp_action.triggered.connect(lambda checked=False: persistent_review_window.start())
mw.form.menuTools.addAction(altp_action)

# Menu action to close persistent window (Alt+Shift+U)
close_unclosable_action = QAction("Close Persistent Review Window", mw)
close_unclosable_action.setShortcut(QKeySequence("Alt+O"))
close_unclosable_action.triggered.connect(lambda checked=False: persistent_review_window.stop())
mw.form.menuTools.addAction(close_unclosable_action)
