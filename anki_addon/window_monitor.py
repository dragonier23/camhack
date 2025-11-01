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

from ctypes import windll, create_unicode_buffer, byref
from ctypes import wintypes
import time
import datetime
import os


class WindowMonitor:
    """Monitor active window changes and trigger callbacks when switching away from Anki."""
    
    def __init__(self, on_non_anki_switch=None):
        """Initialize the WindowMonitor.
        
        Args:
            on_non_anki_switch: Callback function to call when user switches to a non-Anki window
        """
        self.on_non_anki_switch = on_non_anki_switch
        self._timer = None
    
    @staticmethod
    def get_active_window_info():
        """Get information about the currently active (foreground) window.
        
        Returns:
            Dictionary with handle, title, class_name, process_id, and process_name
        """
        user32 = windll.user32
        kernel32 = windll.kernel32

        hwnd = user32.GetForegroundWindow()

        title_buf = create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buf, 512)
        title = title_buf.value

        class_buf = create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        pid_value = pid.value

        # Try psutil first (friendly, cross-version). If not installed, fall back
        # to QueryFullProcessImageNameW to extract the executable name.
        process_name = "Unknown"
        try:
            import psutil

            try:
                p = psutil.Process(pid_value)
                process_name = p.name()
            except Exception:
                process_name = "Unknown"
        except Exception:
            # Fallback: QueryFullProcessImageNameW
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid_value)
            if hproc:
                buf_len = wintypes.DWORD(1024)
                buf = create_unicode_buffer(1024)
                # QueryFullProcessImageNameW: BOOL QueryFullProcessImageNameW(HANDLE, DWORD, LPWSTR, PDWORD)
                try:
                    success = kernel32.QueryFullProcessImageNameW(hproc, 0, buf, byref(buf_len))
                    if success:
                        fullpath = buf.value
                        process_name = os.path.basename(fullpath)
                except Exception:
                    process_name = "Unknown"
                finally:
                    kernel32.CloseHandle(hproc)

        return {
            "handle": int(hwnd),
            "title": title,
            "class_name": class_name,
            "process_id": pid_value,
            "process_name": process_name,
        }
    
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
            initial_window = self.get_active_window_info()
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
            current = self.get_active_window_info()
            
            title = current.get('title', '').lower()
            if 'anki' not in title:
                if self.on_non_anki_switch is not None:
                    self.on_non_anki_switch()
        except Exception:
            # Silent fail - don't interrupt Anki's operation
            pass


def main(poll_ms=500):
    """Standalone main function for running the monitor from command line."""
    if os.name != 'nt':
        print("This script is Windows-specific (uses Win32 APIs).")
        return

    monitor = WindowMonitor()
    previous = monitor.get_active_window_info()
    monitor.print_window_info(previous, event="Initial Window:")

    try:
        while True:
            time.sleep(poll_ms / 1000.0)
            current = monitor.get_active_window_info()
            if current['handle'] != previous['handle']:
                monitor.print_window_info(current)
                previous = current
    except KeyboardInterrupt:
        print('\nMonitoring stopped.')


if __name__ == '__main__':
    main()
