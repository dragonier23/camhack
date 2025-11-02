from datetime import datetime
import os

_DIR = "C:\\Users\\user\\Documents\\GitHub\\camhack\\anki_addon\\log_util"
_LOG_FILE = os.path.join(_DIR, "..", "logs.txt")

def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
