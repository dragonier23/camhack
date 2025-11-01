#!/bin/bash

# Window Change Monitor
# This script detects when the active window changes and prints information about it

echo "Window Monitor Started"
echo "Monitoring for window changes... (Press Ctrl+C to stop)"
echo "----------------------------------------"

# Store the initial window ID
PREVIOUS_WINDOW=$(xdotool getactivewindow 2>/dev/null)

# Check if xdotool is installed
if ! command -v xdotool &> /dev/null; then
    echo "Error: xdotool is not installed."
    echo "Please install it with: sudo apt-get install xdotool"
    exit 1
fi

# Print initial window information
if [ -n "$PREVIOUS_WINDOW" ]; then
    WINDOW_NAME=$(xdotool getwindowname "$PREVIOUS_WINDOW" 2>/dev/null)
    WINDOW_CLASS=$(xdotool getwindowclassname "$PREVIOUS_WINDOW" 2>/dev/null)
    WINDOW_PID=$(xdotool getwindowpid "$PREVIOUS_WINDOW" 2>/dev/null)
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Initial Window:"
    echo "  Window ID: $PREVIOUS_WINDOW"
    echo "  Title: $WINDOW_NAME"
    echo "  Class: $WINDOW_CLASS"
    echo "  PID: $WINDOW_PID"
    echo "----------------------------------------"
fi

# Continuous monitoring loop
while true; do
    # Get current active window
    CURRENT_WINDOW=$(xdotool getactivewindow 2>/dev/null)
    
    # Check if window has changed
    if [ "$CURRENT_WINDOW" != "$PREVIOUS_WINDOW" ] && [ -n "$CURRENT_WINDOW" ]; then
        # Get window information
        WINDOW_NAME=$(xdotool getwindowname "$CURRENT_WINDOW" 2>/dev/null)
        WINDOW_CLASS=$(xdotool getwindowclassname "$CURRENT_WINDOW" 2>/dev/null)
        WINDOW_PID=$(xdotool getwindowpid "$CURRENT_WINDOW" 2>/dev/null)
        
        # Print window change notification
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Window Changed!"
        echo "  Window ID: $CURRENT_WINDOW"
        echo "  Title: $WINDOW_NAME"
        echo "  Class: $WINDOW_CLASS"
        echo "  PID: $WINDOW_PID"
        echo "----------------------------------------"
        
        # Update previous window
        PREVIOUS_WINDOW=$CURRENT_WINDOW
    fi
    
    # Small delay to prevent excessive CPU usage
    sleep 0.5
done
