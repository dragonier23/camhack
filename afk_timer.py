#!/usr/bin/env python3
"""
afk_timer.py

AFK timer that spawns judging images when you're away from keyboard for more than 5 seconds.

Dependencies:
  pip install pynput PyQt5

Usage:
  python3 afk_timer.py

Notes:
  - Spawns multiple windows with judging.png from assets folder after 5 seconds of inactivity
  - Windows close automatically when you return to keyboard
"""

import argparse
import os
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

# Import the image spawning functionality
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from image_spawner import open_images, close_images
    print("Successfully loaded image_spawner module")
except Exception as e:
    print(f"Warning: Could not import image_spawner: {e}")
    print("Image spawning will be disabled.")
    open_images = None
    close_images = None


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
    def __init__(self, afk_threshold=5.0, poll_interval=0.5, image_count=5):
        self.afk_threshold = float(afk_threshold)
        self.poll_interval = float(poll_interval)
        self.image_count = int(image_count)
        self.last_activity = now_ts()
        self.was_afk = False
        self.images_spawned = False
        self.afk_start_time = None
        self.afk_window = None
        self.last_spawn_time = None  # Track when we last spawned images
        self.lock = threading.Lock()
        self._stop = threading.Event()
        
        # Path to the judging image
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_path = os.path.join(script_dir, "assets", "images", "judging.jpeg")

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
                print(f"[{resumed_at}] Welcome back! AFK Duration: {duration_str} | Last active window: {window_str}")
                
                # Close all the judging images when user returns
                if self.images_spawned and close_images:
                    try:
                        close_images()
                        print("Closing all judging images...")
                    except Exception as e:
                        print(f"Error closing images: {e}")
                
                self.was_afk = False
                self.images_spawned = False
                self.last_spawn_time = None
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
        print(f"AFK timer started (threshold: {self.afk_threshold}s). Monitoring keyboard activity... Press Ctrl+C to stop.")
        
        if not os.path.exists(self.image_path):
            print(f"Warning: Image not found at {self.image_path}")
            print("Image spawning will be disabled.")

        try:
            while not self._stop.is_set():
                with self.lock:
                    idle = now_ts() - self.last_activity
                
                # Check if user has been AFK for more than the threshold
                if idle > self.afk_threshold:
                    if not self.was_afk:
                        # Just became AFK
                        self.was_afk = True
                        self.afk_start_time = self.last_activity
                        self.afk_window = get_active_window()
                    
                    # Spawn images initially and then every 5 seconds
                    current_time = now_ts()
                    should_spawn = False
                    
                    if not self.images_spawned:
                        # First spawn
                        should_spawn = True
                        self.last_spawn_time = current_time
                    elif self.last_spawn_time and (current_time - self.last_spawn_time) >= 5.0:
                        # Spawn more every 5 seconds
                        should_spawn = True
                        self.last_spawn_time = current_time
                    
                    if should_spawn and open_images and os.path.exists(self.image_path):
                        try:
                            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            if not self.images_spawned:
                                print(f"[{ts}] AFK detected for {int(idle)}s! Spawning {self.image_count} judging images...")
                            else:
                                print(f"[{ts}] Still AFK! Spawning {self.image_count} more judging images...")
                            success = open_images(self.image_path, spawn_count=self.image_count)
                            if success:
                                # Process Qt events to ensure windows are displayed
                                try:
                                    from image_spawner import _app
                                    if _app:
                                        _app.processEvents()
                                except:
                                    pass
                                self.images_spawned = True
                            else:
                                print("Failed to spawn images")
                        except Exception as e:
                            print(f"Error spawning images: {e}")
                            import traceback
                            traceback.print_exc()
                
                # Process Qt events to keep windows responsive
                try:
                    from image_spawner import _app
                    if _app:
                        _app.processEvents()
                except:
                    pass
                    
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            pass
        finally:
            # Clean up images on exit
            if self.images_spawned and close_images:
                try:
                    close_images()
                except Exception:
                    pass
            self.stop()
            print("AFK timer stopped.")


def parse_args():
    p = argparse.ArgumentParser(description='AFK timer that spawns judging images when idle')
    p.add_argument('--threshold', '-t', type=float, default=5.0, help='Seconds of inactivity before spawning images (default: 5)')
    p.add_argument('--count', '-c', type=int, default=5, help='Number of image windows to spawn (default: 5)')
    p.add_argument('--poll', type=float, default=0.5, help='Polling interval in seconds (default: 0.5)')
    return p.parse_args()


def main():
    args = parse_args()
    timer = AFKTimer(afk_threshold=args.threshold, poll_interval=args.poll, image_count=args.count)
    timer.run()


if __name__ == '__main__':
    main()
