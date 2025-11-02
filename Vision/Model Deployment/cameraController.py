import cv2 as cv
from typing import Tuple
from numpy import ndarray, float32


# Interface which is going to return processed camera images
class CameraController:
    def __init__(self, camera):
        self.cam = camera
        self._scale = 0.7
    
    # Going to yield a processed version of the frame at a given timestep
    def getFrame(self) -> Tuple[ndarray, ndarray, float32 , float32]:
        ret, frame = self.cam.read()

        if not ret:
            raise ConnectionRefusedError("No stream returning from camera.")
        
        cv.imshow("Video", frame)
        image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        original_height, original_width = image.shape[:2]
        resized_img = cv.resize(image, (0, 0), fx= self._scale, fy= self._scale)
        resized_height, resized_width = resized_img.shape[:2]
        height_ratio, width_ratio = original_height / resized_height, original_width / resized_width

        return frame, image, height_ratio, width_ratio