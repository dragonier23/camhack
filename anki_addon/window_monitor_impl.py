import os
import sys
import platform
import subprocess

from .log_util import log

def get_active_window_info():
    """Cross-platform function to get active window information.
    
    Returns:
        Dictionary with handle, title, class_name, process_id, and process_name
        Returns None if detection fails.
    """
    try:
        system = platform.system()
        
        if system == 'Windows':
            return get_active_window_info_nt()
        elif system == 'Linux':
            return get_active_window_info_linux()
        elif system == 'Darwin':
            return get_active_window_info_mac()
        else:
            print(f"Warning: Active window info not implemented for {system}")
            return None
    except Exception as e:
        print(f"Error getting active window info: {e}")
        return None
    
def get_active_window_info_linux():
    """Get information about the currently active window on Linux using xdotool.
    
    Returns:
        Dictionary with handle, title, class_name, process_id, and process_name
        Returns None if detection fails.
    """
    try:
        # Get active window ID
        wid_out = subprocess.check_output(["xdotool", "getactivewindow"], 
                                         stderr=subprocess.DEVNULL, timeout=1)
        wid = wid_out.decode().strip()
        
        # Get window title
        try:
            title_out = subprocess.check_output(["xdotool", "getwindowname", wid], 
                                               stderr=subprocess.DEVNULL, timeout=1)
            title = title_out.decode(errors='ignore').strip()
        except:
            title = "Unknown"
        
        # Get window class name
        try:
            class_out = subprocess.check_output(["xdotool", "getwindowclassname", wid], 
                                               stderr=subprocess.DEVNULL, timeout=1)
            class_name = class_out.decode(errors='ignore').strip()
        except:
            class_name = "Unknown"
        
        # Get process ID
        try:
            pid_out = subprocess.check_output(["xdotool", "getwindowpid", wid], 
                                             stderr=subprocess.DEVNULL, timeout=1)
            pid_value = int(pid_out.decode().strip())
        except:
            pid_value = 0
        
        # Get process name from /proc filesystem
        process_name = "Unknown"
        if pid_value > 0:
            try:
                with open(f"/proc/{pid_value}/comm", "r") as f:
                    process_name = f.read().strip()
            except:
                # Fallback: try to get from cmdline
                try:
                    with open(f"/proc/{pid_value}/cmdline", "r") as f:
                        cmdline = f.read()
                        if cmdline:
                            process_name = os.path.basename(cmdline.split('\0')[0])
                except:
                    pass
        
        return {
            "handle": int(wid) if wid.isdigit() else 0,
            "title": title,
            "class_name": class_name,
            "process_id": pid_value,
            "process_name": process_name,
        }
    except FileNotFoundError:
        print("Warning: xdotool is not installed. Install with: sudo apt-get install xdotool")
        return None
    except subprocess.TimeoutExpired:
        print("Warning: xdotool command timed out")
        return None
    except Exception as e:
        print(f"Warning: Failed to get active window info on Linux: {e}")
        return None

""" 
Eden's version, but returns "python" for Anki for some reason, but still works. Also anki is very laggy/slow, someone should investigate this.
"""
def get_active_window_info_mac():
    """Get information about the currently active window on macOS using PyObjC or AppleScript.
    
    Returns:
        Dictionary with handle, title, class_name, process_id, and process_name
        Returns None if detection fails.
    """
    # Fallback to osascript
    try:
        # Get window title using AppleScript
        ascript_title = '''tell application "System Events"
            set frontApp to first application process whose frontmost is true
            try
                set winName to value of attribute "AXTitle" of front window of frontApp
            on error
                set winName to name of frontApp
            end try
            return winName
        end tell'''
        
        try:
            title_out = subprocess.check_output(["osascript", "-e", ascript_title], 
                                               stderr=subprocess.PIPE, timeout=2)
            title = title_out.decode(errors='ignore').strip()
        except subprocess.TimeoutExpired:
            log("Warning: osascript title command timed out")
            return None
        except Exception as e:
            log(f"Warning: Failed to get window title: {e}")
            return None
        
        
        return {
            "handle": 0,  # macOS doesn't have window handles like Windows
            "title": title,
        }
    except FileNotFoundError:
        log("Warning: osascript not found. This should be available on macOS by default.")
        return None
    except Exception as e:
        log(f"Warning: Failed to get active window info on macOS: {e}")
        return None
    


"""
Xavier's version - but it doesn't work when focused on Anki for some reason
"""
# def get_active_window_info_mac():
#     """Get information about the currently active window on macOS using AppleScript.
    
#     Returns:
#         Dictionary with handle, title, class_name, process_id, and process_name
#         Returns None if detection fails.
#     """
#     try:
#         # Get window title using AppleScript
#         ascript_title = '''tell application "System Events"
#     set frontApp to first application process whose frontmost is true
#     try
#         set winName to value of attribute "AXTitle" of front window of frontApp
#     on error
#         set winName to name of frontApp
#     end try
#     return winName
# end tell'''
        
#         title_out = subprocess.check_output(["osascript", "-e", ascript_title], 
#                                            stderr=subprocess.DEVNULL, timeout=1)
#         title = title_out.decode(errors='ignore').strip()
        
#         # Get process name
#         ascript_proc = '''tell application "System Events"
#     get name of first process whose frontmost is true
# end tell'''
        
#         proc_out = subprocess.check_output(["osascript", "-e", ascript_proc], 
#                                           stderr=subprocess.DEVNULL, timeout=1)
#         process_name = proc_out.decode(errors='ignore').strip()
        
#         # Get process ID
#         ascript_pid = '''tell application "System Events"
#     get unix id of first process whose frontmost is true
# end tell'''
        
#         try:
#             pid_out = subprocess.check_output(["osascript", "-e", ascript_pid], 
#                                              stderr=subprocess.DEVNULL, timeout=1)
#             pid_value = int(pid_out.decode().strip())
#         except:
#             pid_value = 0
        
#         return {
#             "handle": 0,  # macOS doesn't have window handles like Windows
#             "title": title,
#             "class_name": process_name,  # Use process name as class
#             "process_id": pid_value,
#             "process_name": process_name,
#         }
#     except FileNotFoundError:
#         print("Warning: osascript not found. This should be available on macOS by default.")
#         return None
#     except subprocess.TimeoutExpired:
#         print("Warning: osascript command timed out")
#         return None
#     except Exception as e:
#         print(f"Warning: Failed to get active window info on macOS: {e}")
#         return None

    
def get_active_window_info_nt():
    """Get information about the currently active (foreground) window.
    
    Returns:
        Dictionary with handle, title, class_name, process_id, and process_name
    """
    from ctypes import windll, wintypes, create_unicode_buffer, byref
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