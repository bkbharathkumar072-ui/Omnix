import cv2
import mediapipe as mp
import pyautogui
import numpy as np
from math import hypot

# --- CONFIGURATION ---
CONFIDENCE_THRESHOLD = 0.5
SMOOTHING_FACTOR = 0.3
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
LEFT_EYE_IDXS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_IDXS = [362, 385, 387, 263, 373, 380]

class VirtualMouse:
    def __init__(self):
        self.prev_x, self.prev_y = 0, 0
        self.alpha = SMOOTHING_FACTOR
        self.left_clicked = False
        self.right_clicked = False
        
        # Initialize MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1, 
            refine_landmarks=True,
            min_detection_confidence=CONFIDENCE_THRESHOLD
        )
        
        # Performance tuning
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0 

    def calculate_ear(self, landmarks, eye_indices):
        """Calculates Eye Aspect Ratio (EAR) to detect blinks."""
        p = [landmarks[i] for i in eye_indices]
        v1 = hypot(p[1].x - p[5].x, p[1].y - p[5].y)
        v2 = hypot(p[2].x - p[4].x, p[2].y - p[4].y)
        h = hypot(p[0].x - p[3].x, p[0].y - p[3].y)
        return (v1 + v2) / (2.0 * h + 1e-6)

    def smooth_move(self, x, y):
        """Applies exponential smoothing."""
        nx = self.prev_x * (1 - self.alpha) + x * self.alpha
        ny = self.prev_y * (1 - self.alpha) + y * self.alpha
        self.prev_x, self.prev_y = nx, ny
        return nx, ny

    def run(self):
        cap = cv2.VideoCapture(0)
        active = True
        print("System Started. Press 'M' to toggle, 'Q' to quit.")

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success: break

                frame = cv2.flip(frame, 1)
                h, w, _ = frame.shape
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'): break
                elif key == ord('m'): active = not active

                status_color = (0, 255, 0) if active else (0, 0, 255)
                cv2.putText(frame, f"Mouse: {'ACTIVE' if active else 'OFF'}", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

                if results.multi_face_landmarks and active:
                    landmarks = results.multi_face_landmarks[0].landmark
                    
                    # Tracking: Nose tip (landmark 1)
                    nose = landmarks[1]
                    target_x = np.interp(nose.x, [0.3, 0.7], [0, SCREEN_WIDTH])
                    target_y = np.interp(nose.y, [0.3, 0.7], [0, SCREEN_HEIGHT])
                    
                    smooth_x, smooth_y = self.smooth_move(target_x, target_y)
                    pyautogui.moveTo(smooth_x, smooth_y)

                    # Click Logic
                    left_ear = self.calculate_ear(landmarks, LEFT_EYE_IDXS)
                    right_ear = self.calculate_ear(landmarks, RIGHT_EYE_IDXS)

                    if left_ear < 0.18: # Slightly tightened threshold
                        if not self.left_clicked:
                            pyautogui.click()
                            self.left_clicked = True
                    else:
                        self.left_clicked = False

                    if right_ear < 0.18:
                        if not self.right_clicked:
                            pyautogui.rightClick()
                            self.right_clicked = True
                    else:
                        self.right_clicked = False

                cv2.imshow('Eye Tracking Mouse', frame)

        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.face_mesh.close()

if __name__ == "__main__":
    mouse = VirtualMouse()
    mouse.run()
