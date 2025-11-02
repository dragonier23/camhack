from keras.models import load_model
from keras.applications import mobilenet
import cv2 as cv
import dlib
import face_recognition
import numpy as np
from numpy import ndarray, float32
import tensorflow as tf
from imutils import face_utils



# A lot of this code is a rehashing of the open-eye-detector repo, repurposed to provide an interace that measures the 

class EyeTrigger:
    def __init__(self, weights_path, shape_pred_path):
        self.model = load_model(weights_path, compile = False)
        self.predictor = dlib.shape_predictor(shape_pred_path)
        self.left_eye_start_index, self.left_eye_end_index = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        self.right_eye_start_index, self.right_eye_end_index = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
   

    # Directly copied from other repo
    def predict_eye_state(self, image):
        image = cv.resize(image, (20, 10))
        image = image.astype(dtype=np.float32)
            
        image_batch = np.reshape(image, (1, 10, 20, 1))
        image_batch = mobilenet.preprocess_input(image_batch)

        return np.argmax(self.model.predict(image_batch)[0] )

    # Mostly copied from other repo
    def eyesOpen(self, frame: ndarray, rgb_img: ndarray, hratio, wratio) -> bool:
        face_locations = face_recognition.face_locations(rgb_img, model='hog')

        if not len(face_locations): return False

        top, right, bottom, left = face_locations[0]
        x1, y1, x2, y2 = left, top, right, bottom

        x1 = int(x1 * wratio)
        y1 = int(y1 * hratio)
        x2 = int(x2 * wratio)
        y2 = int(y2 * hratio)

        gray_img = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        shape = self.predictor(gray_img, dlib.rectangle(x1, y1, x2, y2))
        face_landmarks = face_utils.shape_to_np(shape)

        left_eye_indices = face_landmarks[self.left_eye_start_index : self.left_eye_end_index]
        (x, y, w, h) = cv.boundingRect(np.array([left_eye_indices]))        
        
        if w <= 0 or h <= 0: return False
        
        left_eye = gray_img[y:y + h, x:x + w]
        left_eye_open = self.predict_eye_state(left_eye)
        

        right_eye_indices = face_landmarks[self.right_eye_start_index : self.right_eye_end_index]
        (x, y, w, h) = cv.boundingRect(np.array([right_eye_indices]))
        
        if w <= 0 or h <= 0: return False
            
        right_eye = gray_img[y:y + h, x:x + w]
        right_eye_open = self.predict_eye_state(right_eye)
                    

        return bool(left_eye_open or right_eye_open)

