#!/usr/bin/env python3
"""
afk_timer.py

Cross-platform AFK timer that resets on keyboard input and prints AFK duration
and active window when the user returns from being idle.

Dependencies:
  pip install pynput

Usage:
  python3 afk_timer.py

Notes:
  - On macOS the script uses `osascript` to query the frontmost app/window.
  - On Linux it tries to use `xdotool` to get the active window title; install with
      sudo apt-get install xdotool
  - On Windows it uses ctypes to call Win32 APIs.
"""

import argparse
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime

try:
    from pynput import keyboard
except Exception as e:
    print("Missing dependency: pynput is required. Install with: pip install pynput")
    raise


def now_ts():
    return time.time()


def get_active_window_mac():
    # Try to get window title using AppleScript
    try:
        # First try to get AXTitle of front window
        ascript = ('tell application "System Events"\n'
                   'set frontApp to first application process whose frontmost is true\n'
                   'try\n'
                   'set winName to value of attribute "AXTitle" of front window of frontApp\n'
                   'on error\n'
                   'set winName to name of frontApp\n'
                   'end try\n'
                   'return winName\n'
                   'end tell')
        out = subprocess.check_output(["osascript", "-e", ascript], stderr=subprocess.DEVNULL)
        title = out.decode(errors='ignore').strip()
        return title
    except Exception:
        # Fallback to simply the frontmost app name
        try:
            out = subprocess.check_output(["osascript", "-e",
                                           'tell application "System Events" to get name of first process whose frontmost is true'],
                                          stderr=subprocess.DEVNULL)
            return out.decode(errors='ignore').strip()
        except Exception:
            return None


def get_active_window_linux():
    # Use xdotool if available
    try:
        out = subprocess.check_output(["xdotool", "getactivewindow", "getwindowname"], stderr=subprocess.DEVNULL)
        return out.decode(errors='ignore').strip()
    except Exception:
        # try wmctrl as an alternative
        try:
            out = subprocess.check_output(["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL)
            wid = out.decode().strip()
            out2 = subprocess.check_output(["xprop", "-id", wid, "WM_NAME"], stderr=subprocess.DEVNULL)
            return out2.decode(errors='ignore').strip()
        except Exception:
            return None


def get_active_window_windows():
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hWnd = user32.GetForegroundWindow()
        if not hWnd:
            return None

        length = user32.GetWindowTextLengthW(hWnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hWnd, buff, length + 1)
        return buff.value
    except Exception:
        return None


def get_active_window():
    system = platform.system()
    if system == 'Darwin':
        return get_active_window_mac()
    elif system == 'Linux':
        return get_active_window_linux()
    elif system == 'Windows':
        return get_active_window_windows()
    else:
        return None


class AFKTimer:
    def __init__(self, poll_interval=0.5):
        self.poll_interval = float(poll_interval)
        self.last_activity = now_ts()
        self.was_afk = False
        self.afk_start_time = None
        self.afk_window = None
        self.lock = threading.Lock()
        self._stop = threading.Event()

    def on_key(self, key):
        with self.lock:
            current_time = now_ts()
            
            if self.was_afk and self.afk_start_time is not None:
                # User returned from AFK - calculate and print duration
                afk_duration = current_time - self.afk_start_time
                resumed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Format duration nicely
                hours = int(afk_duration // 3600)
                minutes = int((afk_duration % 3600) // 60)
                seconds = int(afk_duration % 60)
                
                if hours > 0:
                    duration_str = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    duration_str = f"{minutes}m {seconds}s"
                else:
                    duration_str = f"{seconds}s"
                
                window_str = self.afk_window if self.afk_window else "(unknown)"
                print(f"[{resumed_at}] AFK Duration: {duration_str} | Last active window: {window_str}")
                
                self.was_afk = False
                self.afk_start_time = None
                self.afk_window = None
            
            self.last_activity = current_time

    def start_listener(self):
        # Start keyboard listener in background
        self.listener = keyboard.Listener(on_press=lambda k: self.on_key(k))
        self.listener.start()

    def stop(self):
        self._stop.set()
        try:
            self.listener.stop()
        except Exception:
            pass

    def run(self):
        self.start_listener()
        print("AFK timer started. Monitoring keyboard activity... Press Ctrl+C to stop.")

        try:
            while not self._stop.is_set():
                with self.lock:
                    idle = now_ts() - self.last_activity
                    
                # Mark as AFK when first keystroke stops (no threshold)
                if idle > 0.1 and not self.was_afk:
                    # Just became AFK
                    self.was_afk = True
                    self.afk_start_time = self.last_activity
                    self.afk_window = get_active_window()
                    
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
            print("AFK timer stopped.")


def parse_args():
    p = argparse.ArgumentParser(description='AFK timer that tracks idle time and reports duration when you return')
    p.add_argument('--poll', type=float, default=0.5, help='Polling interval in seconds (default: 0.5)')
    return p.parse_args()


def main():
    args = parse_args()
    timer = AFKTimer(poll_interval=args.poll)
    timer.run()


if __name__ == '__main__':
    main()
