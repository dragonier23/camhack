import subprocess
import time

def get_active_chrome_tab():
    script = '''
    tell application "Google Chrome"
        if (count of windows) = 0 then
            return "No Chrome window open"
        else
            set activeTab to active tab of front window
            return URL of activeTab
        end if
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

prev = None

while True:
    time.sleep(1)
    curr = get_active_chrome_tab()
    if prev != curr:
        prev = curr
        print(f'Switched to URL: {curr}')
