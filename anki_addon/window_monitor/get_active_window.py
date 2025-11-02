import os
import sys
import platform
import subprocess
from typing import Any, Dict, Optional
from .linux import get_active_window_info_linux
from .mac import get_active_window_info_mac
from .windows import get_active_window_info_nt

def get_active_window_info() -> Optional[Dict[str, Any]]:
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

if __name__ == "__main__":
    print(get_active_window_info())
