# pip install pywinauto
from pywinauto import Desktop
import time
import json
from datetime import datetime

POLL_S = 0.25

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def get_chrome_url_pywinauto():
    try:
        desktop = Desktop(backend="uia")
        # pick the first Chrome window it finds
        win = desktop.window(class_name="Chrome_WidgetWin_1", found_index=0)
        if not win.exists(timeout=0.1):
            return None
        # try to find an Edit control (omnibox) inside the Chrome window
        # there may be multiple edit controls; pick the one with non-empty value
        edits = win.descendants(control_type="Edit")
        for e in edits:
            try:
                # many wrappers support .get_value() / .window_text()
                val = e.get_value() if hasattr(e, "get_value") else e.window_text()
                if val and not val.lower().endswith("google chrome"):
                    return val
            except Exception:
                try:
                    txt = e.window_text()
                    if txt:
                        return txt
                except Exception:
                    pass
        # fallback: return window title (may contain page title instead of url)
        return win.window_text()
    except Exception:
        return None

def watch():
    last = None
    print("Watching Chrome (pywinauto). Press Ctrl+C to stop.")
    while True:
        url = get_chrome_url_pywinauto()
        if url != last:
            print(json.dumps({"url": url}))
            last = url
        time.sleep(POLL_S)

if __name__ == "__main__":
    watch()