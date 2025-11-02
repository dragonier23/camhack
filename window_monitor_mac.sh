#!/usr/bin/env bash

# Minimal macOS Window Change Monitor
# Only the polling loop. Keeps a safe AppleScript function and prints changes.

set -euo pipefail

get_front_info() {
    # Returns a tab-separated line: appName\tbundleId\tpid\twindowTitle
    local out
    out=$(osascript \
        -e 'try' \
        -e 'tell application "System Events"' \
        -e 'set frontApp to first application process whose frontmost is true' \
        -e 'set appName to name of frontApp' \
        -e 'set pidNum to unix id of frontApp' \
        -e 'set winTitle to ""' \
        -e 'try' \
        -e 'set winTitle to value of attribute "AXTitle" of front window of frontApp' \
        -e 'end try' \
        -e 'end tell' \
        -e 'set bundleId to ""' \
        -e 'return appName & "\t" & bundleId & "\t" & (pidNum as string) & "\t" & winTitle' \
        -e 'on error errMsg' \
        -e 'return "ERROR:\t" & errMsg' \
        -e 'end try' 2>/dev/null || true)

    printf "%s" "$out"
}

# Initialize previous value (silent)
PREV_INFO=$(get_front_info || echo "")

while true; do
    CUR_INFO=$(get_front_info || echo "")

    if [ -n "$CUR_INFO" ] && [ "$CUR_INFO" != "$PREV_INFO" ]; then
        IFS=$'\t' read -r APP_NAME BUNDLE_ID PID WIN_TITLE <<<"$CUR_INFO"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Frontmost Changed"
        echo "  App: $APP_NAME"
        echo "  Bundle ID: $BUNDLE_ID"
        echo "  PID: $PID"
        echo "  Window Title: $WIN_TITLE"
        PREV_INFO=$CUR_INFO
    fi

    sleep 0.6
done
