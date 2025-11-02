import subprocess


from typing import Optional, Dict, Any
import os
from ..log_util import log


def get_active_window_info_linux() -> Optional[Dict[str, Any]]:
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
        log("Warning: xdotool is not installed. Install with: sudo apt-get install xdotool")
        return None
    except subprocess.TimeoutExpired:
        log("Warning: xdotool command timed out")
        return None
    except Exception as e:
        log(f"Warning: Failed to get active window info on Linux: {e}")
        return None