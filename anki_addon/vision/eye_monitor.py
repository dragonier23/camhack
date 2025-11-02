"""EyeMonitor - Detects when eyes are closed for extended periods using subscriber pattern."""

from typing import Callable, List, Any
import time
import os
import subprocess
import threading
from collections import deque

from ..log_util import log


class EyeMonitor:
    """Monitor eye state and notify subscribers when eyes are closed too long."""
    
    def __init__(self, threshold_seconds: float = 2.0, addon_dir: str = None):
        """Initialize the EyeMonitor.
        
        Args:
            threshold_seconds: How long eyes must be closed before triggering (default 2.0 seconds)
            addon_dir: Path to the addon directory (needed to find vision model)
        """
        self.threshold_seconds = threshold_seconds
        self.addon_dir = addon_dir
        self._subscribers: List[Callable[[bool], None]] = []
        self._eyes_closed_start_time: float | None = None
        self._is_monitoring = False
        self._current_state: bool = False  # Track current eye state
        
        # Subprocess monitoring
        self._vision_process = None
        self._vision_thread = None
        self._check_timer: Any = None
        
        # Track consecutive True/False readings
        self._reading_buffer = deque(maxlen=5)  # Keep last 5 readings
        self._last_emitted_state: bool | None = None
    
    def subscribe(self, callback: Callable[[bool], None]) -> None:
        """Subscribe to eye closure events.
        
        Args:
            callback: Function to call with eyes_closed state (True when closed too long, False when open)
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[bool], None]) -> None:
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
                    # Threshold exceeded - notify subscribers if state changed
                    if not self._current_state:
                        self._current_state = True
                        self._notify_subscribers(True)
        else:
            # Eyes opened - reset timer and notify if state changed
            self._eyes_closed_start_time = None
            if self._current_state:
                self._current_state = False
                self._notify_subscribers(False)
    
    def _notify_subscribers(self, eyes_closed: bool) -> None:
        """Notify all subscribers about eye state change.
        
        Args:
            eyes_closed: True if eyes closed too long, False if eyes opened
        """
        for callback in self._subscribers:
            try:
                callback(eyes_closed)
            except Exception as e:
                # Don't let one subscriber's error affect others
                print(f"Error in eye monitor subscriber: {e}")
    
    def _run_vision_model(self) -> None:
        """Run the vision model in a subprocess and monitor output."""
        if self.addon_dir is None:
            log("Error: addon_dir not provided to EyeMonitor")
            return
        
        venv_python = os.path.join(self.addon_dir, "..", ".venv2", "Scripts", "python.exe")
        trigger_model_path = os.path.join(self.addon_dir, "vision", "triggerModel.py")
        vision_dir = os.path.join(self.addon_dir, "vision")
        
        log("=== Eye Monitor Session Started ===")
        
        try:
            self._vision_process = subprocess.Popen(
                [venv_python, trigger_model_path],
                cwd=vision_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Monitor stdout
            for line in self._vision_process.stdout:
                if not self._is_monitoring:
                    break
                
                line = line.strip()
                
                # Log the output
                log(f"Vision output: {line}")
                
                if line.lower() == 'true':
                    self._reading_buffer.append(True)
                elif line.lower() == 'false':
                    self._reading_buffer.append(False)
                
                # Check if we have 5 readings
                if len(self._reading_buffer) == 5:
                    # All False = eyes closed
                    if all(not reading for reading in self._reading_buffer):
                        if self._last_emitted_state != False:
                            self._last_emitted_state = False
                            log(">>> EYES CLOSED DETECTED <<<")
                            self.on_eyes_state_change(True)  # Eyes closed
                    # All True = eyes open
                    elif all(reading for reading in self._reading_buffer):
                        if self._last_emitted_state != True:
                            self._last_emitted_state = True
                            log(">>> EYES OPEN DETECTED <<<")
                            self.on_eyes_state_change(False)  # Eyes open
            
            log("=== Eye Monitor Session Ended ===")
        
        except Exception as e:
            error_msg = f"Error running vision model: {e}"
            log(error_msg)
            print(error_msg)
    
    def start(self) -> None:
        """Start monitoring eye state using subprocess."""
        self._is_monitoring = True
        
        log("Starting EyeMonitor...")
        # Start vision model in background thread
        self._vision_thread = threading.Thread(target=self._run_vision_model, daemon=True)
        self._vision_thread.start()
    
    def stop(self) -> None:
        """Stop monitoring eye state and cleanup subprocess."""
        self._is_monitoring = False
        self._eyes_closed_start_time = None
        
        # Stop vision process
        if self._vision_process is not None:
            self._vision_process.terminate()
            self._vision_process.wait(timeout=2)
            self._vision_process = None
        
        # Clear buffer
        self._reading_buffer.clear()
        self._last_emitted_state = None
