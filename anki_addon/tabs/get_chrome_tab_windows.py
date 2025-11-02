# pip install pywinauto
from ..pywinauto import Desktop
import time
import json
import ctypes

POLL_S = 0.25
USER32 = ctypes.windll.user32

def _get_foreground_hwnd():
    return USER32.GetForegroundWindow()

def _get_class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    USER32.GetClassNameW(hwnd, buf, 256)
    return buf.value

def _get_window_text(hwnd):
    buf = ctypes.create_unicode_buffer(1024)
    USER32.GetWindowTextW(hwnd, buf, 1024)
    return (buf.value or "").strip()

def _strip_browser_suffix(title: str) -> str:
    for suf in (" - Google Chrome", " - Microsoft Edge", " - Mozilla Firefox"):
        if title.endswith(suf):
            return title[: -len(suf)].strip()
    return title

def get_chrome_url_pywinauto():
    try:
        hwnd = _get_foreground_hwnd()
        if not hwnd:
            return None,None
        
        cls = _get_class_name(hwnd)
        if cls != "Chrome_WidgetWin_1":
            return None,None
        
        raw_title = _get_window_text(hwnd)
        title = _strip_browser_suffix(raw_title) if raw_title else None
        url = None
        try:
            win = Desktop(backend="uia").window(handle=hwnd)

            edits = win.descendants(control_type="Edit")
            for e in edits:
                try:
                    # many wrappers support .get_value() / .window_text()
                    val = e.get_value() if hasattr(e, "get_value") else e.window_text()
                    if val and not val.lower().endswith("google chrome"):
                        url = val
                        break
                except Exception:
                    pass
        except Exception:
            pass
        
        return title or None, url or None
    except Exception:
        return None, None

def watch():
    last = (None,None)
    print("Watching Chrome (pywinauto). Press Ctrl+C to stop.")
    while True:
        title, url = get_chrome_url_pywinauto()
        if (title,url) != last and (title or url):
            last = (title,url)
            print(json.dumps({"title": title, "url": url}, ensure_ascii=False))
        time.sleep(POLL_S)

if __name__ == "__main__":
    watch()