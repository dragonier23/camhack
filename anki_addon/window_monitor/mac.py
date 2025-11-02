import subprocess

from ..log_util import log
from typing import Optional, Dict, Any


def get_active_window_info_mac() -> Optional[Dict[str, Any]]:
    """Get information about the currently active window on macOS.
    
    Uses lsappinfo
    
    Returns:
    
    """
    
    # Fall back to getting just the application name (doesn't need accessibility permissions)
    try:
        # Use shell piping to combine lsappinfo commands
        result = subprocess.run(
            'lsappinfo info -only LSDisplayName "$(lsappinfo front)"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode != 0:
            return None
        
        # Parse output like '"LSDisplayName"="Anki"' or similar
        info_output = result.stdout.strip()
        if 'LSDisplayName"="' in info_output:
            # Extract the name between quotes after LSDisplayName"="
            start = info_output.find('LSDisplayName"="') + 16
            end = info_output.find('"', start)
            app_name = info_output[start:end] if end > start else None
            
            if app_name:
                return {
                    "title": app_name,
                    "handle": 0,
                    "class_name": "",
                    "process_id": "",
                    "process_name": "",
                }
                
    except subprocess.TimeoutExpired:
        log("Warning: lsappinfo command timed out")
    except FileNotFoundError:
        log("Warning: lsappinfo not found")
    except Exception as e:
        log(f"Warning: Failed to get active window info on macOS: {e}")