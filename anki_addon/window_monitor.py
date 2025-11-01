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


def get_active_window_info():
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


def print_window_info(window_info, event="Window Changed!"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {event}")
    print(f"  Window Handle: {window_info['handle']}")
    print(f"  Title: {window_info['title']}")
    print(f"  Class: {window_info['class_name']}")
    print(f"  Process ID: {window_info['process_id']}")
    print(f"  Process Name: {window_info['process_name']}")
    print("----------------------------------------")


def main(poll_ms=500):
    if os.name != 'nt':
        print("This script is Windows-specific (uses Win32 APIs).")
        return

    previous = get_active_window_info()
    print_window_info(previous, event="Initial Window:")

    try:
        while True:
            time.sleep(poll_ms / 1000.0)
            current = get_active_window_info()
            if current['handle'] != previous['handle']:
                print_window_info(current)
                previous = current
    except KeyboardInterrupt:
        print('\nMonitoring stopped.')


if __name__ == '__main__':
    main()
