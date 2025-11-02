"""
Unclosable Window for Anki
Creates a persistent window that displays a card for review and automatically
reopens or brings itself to the front if closed or obscured.
"""

from typing import Optional
import time
from datetime import datetime, timedelta

from aqt import mw
from aqt.qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTimer,
    Qt, QApplication, QEvent, QCloseEvent, QPalette, QKeySequence, QKeyEvent
)
from aqt.utils import showInfo

from .log_util import log
from .window_monitor import get_active_window_info, WindowMonitor, WindowState

class PersistentReviewWindow(QWidget):
    """A window that displays an Anki card and resists being closed or obscured."""
    
    MONITOR_INTERVAL_MS: int = 1000  # Check window state every second
    REVIEW_CHECK_INTERVAL_MS: int = 1000  # Check review completion every 1 second
    REQUIRED_REVIEWS: int = 5
    STATUS_FLASH_DURATION_MS: int = 2000

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.is_active: bool = False
        self.last_activation_time: Optional[float] = None
        self._starting_reviews: int = 0
        self._is_in_anki: bool = False
        self._triggered_by_blacklist: bool = False
        self._distraction_count: int = 0
        self._position_timer: Optional[QTimer] = None
        self.setup_ui()

    def is_dark_mode(self) -> bool:
        palette = QApplication.palette()
        bg = palette.color(QPalette.ColorRole.Window)
        return bg.black() > 128

    def get_reviews_today(self) -> int:
        """Return number of review actions recorded in revlog for local 'today'."""
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

    def _get_title_font_size(self) -> int:
        """Get title font size based on distraction count. Grows increasingly aggressive."""
        base_size = 28
        increment = min(self._distraction_count, 6) * 8
        return base_size + increment

    def _get_stylesheet(self) -> tuple[str, str, str, str]:
        """Generate stylesheets based on dark mode status."""
        is_dark: bool = self.is_dark_mode()
        
        if is_dark:
            title_color = "#e8e8e8"
            card_bg = "#2a2a2a"
            card_border = "#404040"
            text_color = "#d0d0d0"
            status_color = "#a0a0a0"
        else:
            title_color = "#2c3e50"
            card_bg = "#f8f9fa"
            card_border = "#dee2e6"
            text_color = "#2c3e50"
            status_color = "#7f8c8d"
        
        title_font_size = self._get_title_font_size()
        # Calculate min height to accommodate 2 lines with padding
        title_min_height = int(title_font_size * 2.8)  # ~1.4 line height for 2 lines + padding
        
        title_style = f"""
            QLabel {{
                font-size: {title_font_size}px;
                font-weight: bold;
                color: {title_color};
                padding: 30px 20px;
                line-height: 1.4;
                min-height: {title_min_height}px;
            }}
        """
        
        card_style = f"""
            QLabel {{
                font-size: 14px;
                padding: 20px;
                background-color: {card_bg};
                border-radius: 8px;
                border: 1px solid {card_border};
                color: {text_color};
                min-width: 400px;
                max-width: 500px;
            }}
        """
        
        status_style = f"""
            QLabel {{
                font-size: 12px;
                color: {status_color};
                padding: 10px;
            }}
        """
        
        return title_style, card_style, status_style, text_color

    def setup_ui(self) -> None:
        """Initialize the window UI."""
        self.setWindowTitle("📚 LOCK IN!")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        
        # Get stylesheets
        title_style, card_style, status_style, text_color = self._get_stylesheet()
        
        # Main layout (full screen)
        main_layout: QVBoxLayout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Centered content layout (constrains width)
        content_layout: QVBoxLayout = QVBoxLayout()
        content_layout.setContentsMargins(40, 60, 40, 60)
        content_layout.setSpacing(30)
        
        # Title label
        self.title_label: QLabel = QLabel("🎯 You have cards to review!")
        self.title_label.setStyleSheet(title_style)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        content_layout.addWidget(self.title_label)
        
        # Card info label
        self.card_info_label: QLabel = QLabel()
        self.card_info_label.setStyleSheet(card_style)
        self.card_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_info_label.setWordWrap(True)
        content_layout.addWidget(self.card_info_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Review button
        self.review_button: QPushButton = QPushButton("📝 Review Now")
        button_style = self._get_button_stylesheet()
        self.review_button.setStyleSheet(button_style)
        self.review_button.clicked.connect(self.open_reviewer)
        self.review_button.setMaximumWidth(400)
        content_layout.addWidget(self.review_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Status label
        self.status_label: QLabel = QLabel(f"Do {self.get_reviews_today() - self._starting_reviews + self.REQUIRED_REVIEWS} more reviews to close this window.")
        status_label_style = """
            QLabel {
                font-size: 16px;
                color: red;
                padding: 10px;
                font-weight: bold;
            }
        """
        self.status_label.setStyleSheet(status_label_style)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        content_layout.addWidget(self.status_label)
        
        # Footer label with keyboard shortcut
        self.footer_label: QLabel = QLabel("⌨️ Press Alt + O/Option + O to stop (demo only)")
        footer_style = """
            QLabel {
                font-size: 10px;
                color: #999999;
                padding: 5px;
                font-style: italic;
            }
        """
        self.footer_label.setStyleSheet(footer_style)
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.footer_label)
        
        # Add content layout to main layout with centering
        content_wrapper = QWidget()
        content_wrapper.setLayout(content_layout)
        main_layout.addStretch()
        main_layout.addWidget(content_wrapper, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.setGeometry(rect)
        self.setFixedSize(self.size())
        self._fixed_geometry = self.geometry()
        self.load_card_info()

    def _get_button_stylesheet(self) -> str:
        """Generate button stylesheet based on dark mode status."""
        is_dark: bool = self.is_dark_mode()
        
        if is_dark:
            return """
                QPushButton {
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px;
                    background-color: #4a90e2;
                    color: white;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #357abd;
                }
                QPushButton:pressed {
                    background-color: #1e4788;
                }
            """
        else:
            return """
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
            """
        
    def _get_distraction_message(self) -> str:
        """Generate a funny, increasingly aggressive message based on distraction count."""
        self._distraction_count += 1
        
        messages = [
            "😅 There is no point in escaping.",
            "😤 Really? Again? You need to LOCK IN!",
            "🤨 Okay. BACK TO REVIEWS.",
            "😠 STOP RUNNING AWAY! Your cards are judging you.",
            "🤬 ARE YOU KIDDING ME?! THIS IS THE FIFTH TIME!",
            "🚨 EVERY TIME YOU LEAVE I GAIN POWER. DO YOUR REVIEWS.",
            "💀 YOU ARE ONE WITH ANKI. YOU CANNOT ESCAPE.",
            "👹 YOUR DISTRACTION ONLY MAKES ME STRONGER.",
        ]
        
        # Use increasingly aggressive messages, cycling through if needed
        return messages[min(self._distraction_count - 1, len(messages) - 1)]
    
    def load_card_info(self) -> None:
        """Load and display information about pending cards."""
        if not mw or not mw.col:
            return
        
        # Get card counts
        due_counts = mw.col.sched.counts()
        new_cards: int = due_counts[0] if len(due_counts) > 0 else 0
        learning: int = due_counts[1] if len(due_counts) > 1 else 0
        review: int = due_counts[2] if len(due_counts) > 2 else 0
        
        total: int = new_cards + learning + review
        
        if total == 0:
            self.card_info_label.setText("Great job! Come back later for more reviews.")
            self.review_button.setEnabled(False)
        else:
            info_text: str = f"""
            <div style='text-align: center;'>
            <p><b>Cards Due: {total}</b></p>
            <p>🆕 New: {new_cards} | 📚 Learning: {learning} | 🔄 Review: {review}</p>
            </div>
            """
            self.card_info_label.setText(info_text)

    def start(self) -> None:
        log('start unclosable window')
        """Start monitoring and display the persistent window."""
        self.is_active = True
        self.last_activation_time = time.time()
        self._starting_reviews = self.get_reviews_today()
        
        # Start the position reset timer
        if self._position_timer is None:
            self._position_timer = QTimer()
            self._position_timer.timeout.connect(self._enforce_position)
            self._position_timer.start(1000)  # Every second
        
        self.load_card_info()
        self._bring_to_front()

    def stop(self) -> None:
        """Close the window, stop all monitoring, and quit Anki."""
        self.is_active = False
        # Stop the position timer
        if self._position_timer is not None:
            self._position_timer.stop()
            self._position_timer = None
        self.close()
        tmp = self.REQUIRED_REVIEWS
        self.REQUIRED_REVIEWS = 0
        mw.close()
    def _enforce_position(self) -> None:
        """Enforce window position and focus (called every second)."""
        if not self.is_active:
            return
        self.setGeometry(self._fixed_geometry)
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)

    def _bring_to_front(self) -> None:
        """Show the window and bring it to the front."""
        if not self.is_active:
            return
        self.show()
        self._enforce_position()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Intercept close events and reopen the window instead."""
        if self.is_active:
            event.ignore()  # Prevent closing
            self._bring_to_front()
            self.status_label.setText("⚠️ Cannot close! Complete your reviews first!")
            # Flash the status message
            QTimer.singleShot(self.STATUS_FLASH_DURATION_MS, lambda: self.status_label.setText("Window will reopen if closed"))
        else:
            event.accept()

    def changeEvent(self, event: QEvent) -> None:
        """Handle window state changes."""
        if event.type() == QEvent.Type.WindowStateChange:
            # If minimized, restore it
            if self.isMinimized() and self.is_active:
                QTimer.singleShot(500, self._bring_to_front)
        super().changeEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events. Alt+O will stop the window, Cmd+Q is blocked."""
        # Block Command+Q (Cmd+Q on Mac)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Q:
                if self.is_active:
                    log("Cmd+Q pressed - blocked while reviews active")
                    self.status_label.setText("⚠️ Cannot quit! Complete your reviews first!")
                    QTimer.singleShot(self.STATUS_FLASH_DURATION_MS, lambda: self.status_label.setText(f"Do {self.get_reviews_today() - self._starting_reviews} more reviews to close this window."))
                    return
        
        # Handle Alt+O to stop the window
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            if event.key() == Qt.Key.Key_O:
                log("Alt+O pressed in window - stopping")
                self.stop()
                return
        super().keyPressEvent(event)
        
    def open_reviewer(self) -> None:
        """Open the Anki reviewer to actually review cards."""
        try:
            if mw and mw.col:
                # Switch to review mode
                mw.moveToState("review")
                # Temporarily deactivate monitoring while reviewing
                self.is_active = False
                self.hide()
        except Exception as e:
            showInfo(f"Error opening reviewer: {str(e)}")

    def on_window_state_change(self, prev_state: WindowState, curr_state: WindowState, curr_title: str) -> None:
        """Handle window state changes from the window monitor.
        
        Behavior:
        1. When user switches to a blacklisted app, start forcing review popup
        2. When user switches to Anki, allow them to review (popup stays hidden if they're reviewing)
        3. When user switches to any other app (not Anki) and hasn't completed reviews, force popup again
        4. When required reviews are completed, stop the popup permanently
        
        Args:
            prev_state: Previous window state
            curr_state: Current window state
            curr_title: Current window title (for debugging)
        """
        curr_reviews: int = self.get_reviews_today() - self._starting_reviews
        has_completed_reviews: bool = curr_reviews >= self.REQUIRED_REVIEWS
        
        log(f'Window state change: {prev_state.value} -> {curr_state.value} (title: {curr_title})')
        
        # If user has completed required reviews, stop everything
        if has_completed_reviews:
            log('Reviews completed! Stopping popup.')
            if self.is_active:
                self.stop()
                self._triggered_by_blacklist = False
            return
        
        if curr_state == WindowState.BLACKLISTED:
            if not self.is_active:
                log('Switched to blacklisted app - triggering popup')
                self.start()
                self._triggered_by_blacklist = True
        
        # Check if currently in Anki
        is_anki: bool = curr_state == WindowState.WHITELISTED and 'anki' in curr_title.lower()
        
        if not is_anki and self._triggered_by_blacklist:
            # User switched to a non-Anki app
            log('Switched away from Anki - triggering popup')
            if not self.is_active:
                self.start()
            self._bring_to_front()
            self.is_active = True
            
            # Show aggressive message in title for distraction
            aggressive_msg = self._get_distraction_message()
            self.title_label.setText(aggressive_msg)
            # Refresh stylesheet to update dynamic font size
            title_style, _, _, _ = self._get_stylesheet()
            self.title_label.setStyleSheet(title_style)
