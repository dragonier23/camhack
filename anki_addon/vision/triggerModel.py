import cv2 as cv
import dlib
import face_recognition
import numpy as np
import onnx
import torch
from imutils import face_utils
from numpy import float32, ndarray
from onnx2pytorch import ConvertModel


from cameraController import CameraController

# A lot of this code is a rehashing of the open-eye-detector repo, repurposed to provide an interace that measures the 

class EyeTrigger:
    def __init__(self, blueprint_path, weights_path, shape_pred_path):
        if torch.cuda.is_available():
            self.device = torch.device('cuda')
        elif torch.backends.mps.is_available():
            self.device = torch.device('mps')
        else:
            self.device = torch.device('cpu')

        onnx_model = onnx.load(blueprint_path)
        self.model = ConvertModel(onnx_model)
        self.model.load_state_dict(torch.load(weights_path))
        self.model.eval()
        self.model.to(self.device)

        self.predictor = dlib.shape_predictor(shape_pred_path)
        self.left_eye_start_index, self.left_eye_end_index = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        self.right_eye_start_index, self.right_eye_end_index = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
   
    '''
    # Directly copied from other repo
    def predict_eye_state(self, image):
        image = cv.resize(image, (20, 10))
        image = image.astype(dtype=np.float32)
            
        image_batch = np.reshape(image, (1, 10, 20, 1))
        image_batch = mobilenet.preprocess_input(image_batch)

        return np.argmax(self.model.predict(image_batch)[0] )
    '''

    def predict_eye_state(self, image):
        # TOOD: !ssize.empty() in cv.resize; image is empty/no face is detected... so need to consider that.
        image = cv.resize(image, (20, 10))
        image = image.astype(dtype=np.float32)
        image_tensor = torch.from_numpy(image)

        image_batch = image_tensor.unsqueeze(0).unsqueeze(0)
        image_batch = (image_batch / 127.5) - 1.0
        image_batch = image_batch.to(self.device)

        with torch.no_grad():
            output = self.model(image_batch)

        prediction_index = torch.argmax(output, dim=1).item()

        return prediction_index

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

if __name__ == "__main__":
    torch_weights_path = 'Weights/torch_weights.pth'
    torch_blueprint = "Weights/my_model.onnx"
    landmark_detection_path = "Weights/68_face_landmarks_predictor.dat"
    triggerModel = EyeTrigger(torch_blueprint, torch_weights_path, landmark_detection_path)

    cam = cv.VideoCapture(0)

    if not cam.isOpened():
        raise EnvironmentError("Camera was not able to be opened.")

    controller = CameraController(cam)
    try:
        while True:
            try:
                frameData = controller.getFrame()
                print(triggerModel.eyesOpen(*frameData))

                if cv.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as e:
                print(f"Error during eye state detection: {e}")
    finally:
        cam.release()
        cv.destroyAllWindows()