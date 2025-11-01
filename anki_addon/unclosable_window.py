"""
Unclosable Window for Anki
Creates a persistent window that displays a card for review and automatically
reopens or brings itself to the front if closed or obscured.
"""

from aqt import mw
from aqt.qt import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextBrowser, QTimer,
    Qt, QApplication, QEvent, QCloseEvent, QPalette
)
from aqt.reviewer import Reviewer
from aqt.utils import showInfo
import time

from .log_util import log
from .window_monitor_impl import get_active_window_info

# Qt6 uses enums nested under ColorRole; use ColorRole.Window here.

# 211 for dark
# 10 for light

# Global reference to keep the window alive
_persistent_window = None

class PersistentReviewWindow(QWidget):
    """A window that displays an Anki card and resists being closed or obscured."""
    def get_reviews_today(self):
        """Return number of review actions recorded in revlog for local 'today'."""
        from datetime import datetime, timedelta
        # midnight local time
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        try:
            cnt = mw.col.db.scalar(
                "select count() from revlog where id >= ? and id < ?", start_ms, end_ms
            )
            return int(cnt or 0)
        except Exception:
            return 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_monitoring()
        self.is_active = True
        self.last_activation_time = time.time()
        self._starting_reviews = self.get_reviews_today()

    def is_dark_mode(self):
        palette = QApplication.palette()
        bg = palette.color(QPalette.ColorRole.Window)
        showInfo(str(bg.black()))
        
    def setup_ui(self):
        """Initialize the window UI."""
        self.setWindowTitle("📚 Time to Review!")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title label
        self.title_label = QLabel("🎯 You have cards to review!")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Card info label
        self.card_info_label = QLabel()
        self.card_info_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }
        """)
        self.card_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_info_label.setWordWrap(True)
        layout.addWidget(self.card_info_label)
        
        # # Card content display: use QTextBrowser so HTML is rendered
        # self.card_display = QTextBrowser()
        # self.card_display.setStyleSheet("""
        #     QTextBrowser {
        #         font-size: 16px;
        #         padding: 20px;
        #         background-color: white;
        #         border: 2px solid #3498db;
        #         border-radius: 8px;
        #         min-height: 150px;
        #     }
        # """)
        # self.card_display.setOpenExternalLinks(True)
        # self.card_display.setReadOnly(True)
        # layout.addWidget(self.card_display)
        
        # Review button
        self.review_button = QPushButton("📝 Review Now")
        self.review_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.review_button.clicked.connect(self.open_reviewer)
        layout.addWidget(self.review_button)
        
        # Status label
        self.status_label = QLabel("Window will reopen if closed")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #7f8c8d;
                padding: 5px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setGeometry(rect)
        self.setFixedSize(self.size())
        self._fixed_geometry = self.geometry()
        # self.resize(800, 600)
        self.load_card_info()
        
    def load_card_info(self):
        """Load and display information about pending cards."""
        if not mw or not mw.col:
            return
        
        # Get card counts
        due_counts = mw.col.sched.counts()
        new_cards = due_counts[0] if len(due_counts) > 0 else 0
        learning = due_counts[1] if len(due_counts) > 1 else 0
        review = due_counts[2] if len(due_counts) > 2 else 0
        
        total = new_cards + learning + review
        
        if total == 0:
            self.card_info_label.setText("Great job! Come back later for more reviews.")
            self.review_button.setEnabled(False)
        else:
            info_text = f"""
            <div style='text-align: center;'>
            <p><b>Cards Due: {total}</b></p>
            <p>🆕 New: {new_cards} | 📚 Learning: {learning} | 🔄 Review: {review}</p>
            </div>
            """
            self.card_info_label.setText(info_text)
            
    def setup_monitoring(self):
        """Set up timers to monitor window state and bring it back if needed."""
        # Timer to check if window is obscured 
        self.monitor_window_timer = QTimer(self)
        self.monitor_window_timer.timeout.connect(self.check_window_state)
        self.monitor_window_timer.start(1000)  # Check every second
        
        self.load_card_info()
        
    def check_window_state(self):
        """Check if window needs to be brought to front."""
        if not self.is_active:
            return
            
        self.show_and_raise()
            
    def show_and_raise(self):
        """Show the window and bring it to the front."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.setGeometry(self._fixed_geometry)
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        
    def closeEvent(self, event: QCloseEvent):
        """Intercept close events and reopen the window instead."""
        if self.is_active:
            event.ignore()  # Prevent closing
            self.show_and_raise()
            self.status_label.setText("⚠️ Cannot close! Complete your reviews first!")
            # Flash the status message
            QTimer.singleShot(2000, lambda: self.status_label.setText("Window will reopen if closed"))
        else:
            event.accept()
            
    def changeEvent(self, event: QEvent):
        """Handle window state changes."""
        if event.type() == QEvent.Type.WindowStateChange:
            # If minimized, restore it
            if self.isMinimized() and self.is_active:
                QTimer.singleShot(500, self.show_and_raise)
        super().changeEvent(event)
        
    def open_reviewer(self):
        """Open the Anki reviewer to actually review cards."""
        try:
            if mw and mw.col:
                # Switch to review mode
                mw.moveToState("review")
                # Temporarily deactivate monitoring while reviewing
                self.is_active = False
                self.hide()

                # Timer to check if reviews have been completed before "freeing" the user
                self.review_completion_timer = QTimer(self)
                self.review_completion_timer.timeout.connect(self.check_review_completion)
                self.review_completion_timer.start(5000)  # Check every 5 seconds
        except Exception as e:
            showInfo(f"Error opening reviewer: {str(e)}")
            
    def check_review_completion(self):
        """Check if user has completed reviews and reactivate if needed."""
        if not self.is_active:
            REQUIRED_REVIEWS = 2
            curr_reviews = self.get_reviews_today()- self._starting_reviews
            window_info = get_active_window_info()
            # log(f'curr_reviews = {curr_reviews}, app = {window_info["title"]}')
            is_focused = "python" in window_info["title"].lower()
            is_done = curr_reviews > REQUIRED_REVIEWS
            if not is_focused and not is_done:
                log('BADD!!')
                self.is_active = True
            elif is_done:
                log('reviews done!')
                self.permanently_close()



    def permanently_close(self):
        global _persistent_window
        """Actually close the window (used when stopping monitoring)."""
        self.is_active = False
        self.monitor_window_timer.stop()
        if self.review_completion_timer: self.review_completion_timer.stop()
        self.close()
        _persistent_window = None




def open_unclosable_window():
    """Open the persistent review window."""
    global _persistent_window
    
    if _persistent_window is not None:
        # Window already exists, just bring it to front
        _persistent_window.show_and_raise()
        return
    
    try:
        if not mw or not mw.col:
            showInfo("Please open a collection first!")
            return
            
        _persistent_window = PersistentReviewWindow()
        _persistent_window.show_and_raise()
        
    except Exception as e:
        showInfo(f"Error opening window: {str(e)}")


def close_unclosable_window():
    """Close the persistent window (if user really needs to stop it)."""
    global _persistent_window
    
    if _persistent_window is not None:
        _persistent_window.permanently_close()
        _persistent_window = None
