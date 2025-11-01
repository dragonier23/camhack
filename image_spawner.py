#!/usr/bin/env python3
"""
Standalone image spawner that works without Anki.
Uses PyQt5 to spawn multiple image windows at random positions.
"""

import os
import random
import sys

try:
    from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtCore import Qt
except ImportError:
    print("Error: PyQt5 is required. Install with: pip install PyQt5")
    sys.exit(1)


# Keep references to the windows so they are not garbage-collected
_image_windows = []
_app = None


def init_qt_app():
    """Initialize QApplication if not already done."""
    global _app
    if _app is None:
        _app = QApplication.instance()
        if _app is None:
            _app = QApplication(sys.argv)
    return _app


def open_images(image_path: str, spawn_count: int = 5):
    """
    Open multiple windows showing the specified image.
    Each window is placed at a random location on the screen.
    
    Args:
        image_path: Path to the image file to display
        spawn_count: Number of windows to spawn (default: 5)
    """
    app = init_qt_app()
    
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return False
    
    # Limit the number of windows to a reasonable value
    spawn_count = min(spawn_count, 20)  # Max 20 windows
    
    for i in range(spawn_count):
        w = QWidget()
        w.setWindowTitle(f"👁️ Judging You #{i+1}")
        w.setWindowFlags(Qt.WindowStaysOnTopHint)  # Stay on top
        
        layout = QVBoxLayout(w)
        label = QLabel()
        pix = QPixmap(image_path)
        
        if pix.isNull():
            print(f"Error: Failed to load image from {image_path}")
            return False
        
        # Limit the displayed image to max width=200 and max height=300 while keeping aspect ratio
        max_w, max_h = 200, 300
        scaled_pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled_pix)
        layout.addWidget(label)
        w.setLayout(layout)
        
        # Size the window to the scaled image
        w.resize(scaled_pix.width(), scaled_pix.height())
        
        # Compute a random position on the user's screen
        try:
            screen = app.primaryScreen()
            if screen is None:
                raise RuntimeError("no primary screen")
            geom = screen.availableGeometry()
            x_min = geom.x()
            y_min = geom.y()
            x_max = geom.x() + max(0, geom.width() - w.width())
            y_max = geom.y() + max(0, geom.height() - w.height())
            
            if x_max < x_min:
                x = x_min
            else:
                x = random.randint(x_min, x_max)
            
            if y_max < y_min:
                y = y_min
            else:
                y = random.randint(y_min, y_max)
        except Exception:
            # Fallback if screen geometry isn't available
            x = 100 + random.randint(0, 300)
            y = 100 + random.randint(0, 300)
        
        w.move(x, y)
        w.show()
        _image_windows.append(w)
    
    return True


def close_images():
    """Close all image windows opened by this module."""
    global _image_windows
    while _image_windows:
        w = _image_windows.pop()
        try:
            w.close()
        except Exception:
            # best-effort close; ignore errors
            pass


def test_spawn():
    """Test function to spawn images with a test image."""
    # Try to find judging.jpeg in assets folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_image = os.path.join(script_dir, "assets", "judging.jpeg")
    
    if not os.path.exists(test_image):
        print(f"Test image not found at {test_image}")
        print("Please provide a valid image path.")
        return
    
    print(f"Spawning 5 windows with {test_image}...")
    success = open_images(test_image, spawn_count=5)
    
    if success:
        print("Images spawned! They will stay open.")
        print("Close them manually or press Ctrl+C to exit and clean up.")
        
        # Keep the app running
        app = QApplication.instance()
        if app:
            try:
                sys.exit(app.exec_())
            except KeyboardInterrupt:
                print("\nClosing all images...")
                close_images()


if __name__ == "__main__":
    test_spawn()
