import subprocess
import time

SEP = "|||||"

def get_active_chrome_tab():
    script = f'''
    tell application "Google Chrome"
        if (count of windows) = 0 then
            return "{SEP}"
        else
            set activeTab to active tab of front window
            set theTitle to title of activeTab
            return theTitle & "{SEP}" & URL of activeTab
        end if
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True
    )
    out = (result.stdout or "").strip()
    if SEP not in out:
        return None, None
    title, url = out.split(SEP,1)
    title = title.strip() or None
    url = url.strip() or None
    if not title and not url:
        return None, None
    return title, url

prev = None

while True:
    time.sleep(1)
    title, curr = get_active_chrome_tab()
    if (title, curr) != prev and (title or curr):
        prev = (title, curr)
        print(f'Switched to URL: {curr}, title: {title}')
