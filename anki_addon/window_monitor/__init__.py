"""Window Change Monitor for Windows (Python)

This script monitors the active (foreground) window on Windows and
prints information when it changes. It mirrors the behavior of the
PowerShell `window_monitor.ps1` in this repo.

It uses ctypes to call Win32 APIs (GetForegroundWindow, GetWindowTextW,
GetClassNameW, GetWindowThreadProcessId). For process name lookup it
first tries `psutil` (if installed) then falls back to QueryFullProcessImageNameW.

Usage: run on Windows:
    python window_monitor.py

Ctrl+C stops the monitor loop.
"""

from typing import Callable
from .get_active_window import get_active_window_info
import time
import datetime
import os
from enum import Enum


class WindowState(Enum):
    """Enum representing the classification state of a window."""
    WHITELISTED = "whitelisted"
    BLACKLISTED = "blacklisted"
    UNCLASSIFIED = "unclassified"


# Export WindowState at module level for easy importing
__all__ = ['WindowState', 'WindowMonitor']


class WindowMonitor:
    """Monitor active window changes and trigger callbacks when switching between windows."""
    
    WHITELIST = [
        'anki',
        'microsoft teams',
        'outlook',
        'visual studio code',
        'google chrome',
        'comet',
    ]

    BLACKLIST = [
        'discord',
        'whatsapp',
    ]

    def __init__(self):
        """Initialize the WindowMonitor."""
        self._subscribers: list[Callable[[WindowState, WindowState, str], None]] = []
        self._timer = None
        self._previous_state = None

    def subscribe(self, callback: Callable[[WindowState, WindowState, str], None]):
        """Subscribe to window state change notifications.
        
        Args:
            callback: Function that takes (prev_state: WindowState, curr_state: WindowState)
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[WindowState, WindowState, str], None]):
        """Unsubscribe from window state change notifications.
        
        Args:
            callback: Function to remove from subscribers
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _classify_window(self, window_info: dict) -> WindowState:
        """Classify a window based on its title.
        
        Args:
            window_info: Dictionary with window information
            
        Returns:
            WindowState enum value
        """
        if window_info is None:
            return WindowState.UNCLASSIFIED
        
        title = window_info.get('title', '').lower()
        
        if any(kw in title for kw in self.BLACKLIST):
            return WindowState.BLACKLISTED
        elif any(kw in title for kw in self.WHITELIST):
            return WindowState.WHITELISTED
        else:
            return WindowState.UNCLASSIFIED

    def _notify_subscribers(self, prev_state: WindowState, curr_state: WindowState, curr_title: str):
        """Notify all subscribers of a state change.
        
        Args:
            prev_state: Previous WindowState
            curr_state: Current WindowState
        """
        for callback in self._subscribers:
            try:
                callback(prev_state, curr_state, curr_title)
            except Exception as e:
                # Don't let one subscriber's error affect others
                import traceback
                print(f"Subscriber callback error: {e}")
                traceback.print_exc()

    @staticmethod
    def print_window_info(window_info: dict, event: str = "Window Changed!"):
        """Print formatted window information.
        
        Args:
            window_info: Dictionary with window information
            event: Event description to print
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {event}")
        print(f"  Window Handle: {window_info['handle']}")
        print(f"  Title: {window_info['title']}")
        print(f"  Class: {window_info['class_name']}")
        print(f"  Process ID: {window_info['process_id']}")
        print(f"  Process Name: {window_info['process_name']}")
        print("----------------------------------------")

    def start(self, poll_interval_ms: int = 500):
        """Start monitoring window changes.
        
        Args:
            poll_interval_ms: How often to check for window changes (in milliseconds)
        """
        try:
            from aqt.qt import QTimer
            
            # Get initial window state
            initial_window = get_active_window_info()
            self._previous_state = self._classify_window(initial_window)
            
            # Create timer for periodic checks
            self._timer = QTimer()
            self._timer.timeout.connect(self._check_window_change)
            self._timer.start(poll_interval_ms)
        except Exception:
            # If initialization fails, just don't start monitoring
            pass
    
    def stop(self):
        """Stop monitoring window changes."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
    
    def _check_window_change(self):
        """Called periodically to check if the active window state changed."""
        try:
            current_window = get_active_window_info()
            current_state = self._classify_window(current_window)
            
            # Only notify if state changed
            if current_state != self._previous_state:
                self._notify_subscribers(self._previous_state, current_state, current_window.get('title', ''))
                self._previous_state = current_state
                
        except Exception as e:
            # Silent fail - don't interrupt Anki's operation
            # But log for debugging
            import traceback
            print(f"Window monitor error: {e}")
            traceback.print_exc()


def main(poll_ms=500):
    """Standalone main function for running the monitor from command line."""
    if os.name != 'nt':
        print("This script is Windows-specific (uses Win32 APIs).")
        return

    def on_state_change(prev_state, curr_state):
        """Example subscriber callback."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] State Changed: {prev_state.value} -> {curr_state.value}")
    
    monitor = WindowMonitor()
    monitor.subscribe(on_state_change)
    
    initial_window = get_active_window_info()
    WindowMonitor.print_window_info(initial_window, event="Initial Window:")
    print(f"Initial State: {monitor._classify_window(initial_window).value}")
    
    monitor.start(poll_ms)

    try:
        print("\nMonitoring window state changes... (Press Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nMonitoring stopped.')
        monitor.stop()


if __name__ == '__main__':
    main()