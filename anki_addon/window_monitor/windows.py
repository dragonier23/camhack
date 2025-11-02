import os
from typing import Dict, Any

def get_active_window_info_nt() -> Dict[str, Any]:
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
        import psutil  # type: ignore
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