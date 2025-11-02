"""EyeMonitor - Detects when eyes are closed for extended periods using subscriber pattern."""

from typing import Callable, List
import time


class EyeMonitor:
    """Monitor eye state and notify subscribers when eyes are closed too long."""
    
    def __init__(self, threshold_seconds: float = 2.0):
        """Initialize the EyeMonitor.
        
        Args:
            threshold_seconds: How long eyes must be closed before triggering (default 2.0 seconds)
        """
        self.threshold_seconds = threshold_seconds
        self._subscribers: List[Callable[[], None]] = []
        self._eyes_closed_start_time: float | None = None
        self._is_monitoring = False
    
    def subscribe(self, callback: Callable[[], None]) -> None:
        """Subscribe to eye closure events.
        
        Args:
            callback: Function to call when eyes are closed for too long
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[], None]) -> None:
        """Unsubscribe from eye closure events.
        
        Args:
            callback: Function to remove from subscribers
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def on_eyes_state_change(self, eyes_closed: bool) -> None:
        """Called when eye state changes (opened/closed).
        
        Args:
            eyes_closed: True if eyes are closed, False if open
        """
        current_time = time.time()
        
        if eyes_closed:
            # Eyes just closed or are still closed
            if self._eyes_closed_start_time is None:
                # Just closed - start timer
                self._eyes_closed_start_time = current_time
            else:
                # Still closed - check duration
                closed_duration = current_time - self._eyes_closed_start_time
                if closed_duration >= self.threshold_seconds:
                    # Threshold exceeded - notify subscribers
                    self._notify_subscribers()
                    # Reset to avoid repeated notifications
                    self._eyes_closed_start_time = current_time
        else:
            # Eyes opened - reset timer
            self._eyes_closed_start_time = None
    
    def _notify_subscribers(self) -> None:
        """Notify all subscribers that eyes have been closed too long."""
        for callback in self._subscribers:
            try:
                callback()
            except Exception as e:
                # Don't let one subscriber's error affect others
                print(f"Error in eye monitor subscriber: {e}")
    
    def start(self) -> None:
        """Start monitoring (placeholder for future implementation)."""
        self._is_monitoring = True
    
    def stop(self) -> None:
        """Stop monitoring (placeholder for future implementation)."""
        self._is_monitoring = False
        self._eyes_closed_start_time = None
