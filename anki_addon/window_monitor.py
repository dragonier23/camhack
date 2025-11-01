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

from .window_monitor_impl import get_active_window_info
import time
import datetime
import os


class WindowMonitor:
    """Monitor active window changes and trigger callbacks when switching away from Anki."""
    
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

    def __init__(self, on_blacklisted_switch=None):
        """Initialize the WindowMonitor.
        
        Args:
            on_blacklisted_switch: Callback function to call when user switches to a blacklisted window
        """
        self.on_blacklisted_switch = on_blacklisted_switch
        self._timer = None

    @staticmethod
    def print_window_info(window_info, event="Window Changed!"):
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
    
    def start(self, poll_interval_ms=500):
        """Start monitoring window changes.
        
        Args:
            poll_interval_ms: How often to check for window changes (in milliseconds)
        """
        try:
            from aqt.qt import QTimer
            
            # Get initial window
            initial_window = get_active_window_info()
            self._previous_window_handle = initial_window.get('handle')
            
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
        """Called periodically to check if the active window changed to something outside Anki."""
        try:
            current = get_active_window_info()
            
            title = current.get('title', '').lower()
            if any(kw in title for kw in self.BLACKLIST):
                if self.on_blacklisted_switch is not None:
                    self.on_blacklisted_switch()
        except Exception:
            # Silent fail - don't interrupt Anki's operation
            pass


def main(poll_ms=500):
    """Standalone main function for running the monitor from command line."""
    if os.name != 'nt':
        print("This script is Windows-specific (uses Win32 APIs).")
        return

    previous = get_active_window_info()
    WindowMonitor.print_window_info(previous, event="Initial Window:")

    try:
        while True:
            time.sleep(poll_ms / 1000.0)
            current = get_active_window_info()
            if current['handle'] != previous['handle']:
                WindowMonitor.print_window_info(current)
                previous = current
    except KeyboardInterrupt:
        print('\nMonitoring stopped.')


if __name__ == '__main__':
    main()
