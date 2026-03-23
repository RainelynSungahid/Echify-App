#shared_camera.py
import cv2
import threading
import time


class SharedCamera:
    def __init__(self, device=0):  # 0 = default laptop webcam
        self.device = device
        self.cap = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return

        retries = 5
        for attempt in range(retries):
            self.cap = cv2.VideoCapture(self.device)
            if self.cap.isOpened():
                break

            print(f"Warning: Camera open failed on device {self.device}, retry {attempt + 1}/{retries}")
            time.sleep(1)

        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera device: {self.device}")

        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        print(f"Shared camera started on device index {self.device}")

    def _reader_loop(self):
        while self.running:
            ok, frame = self.cap.read()
            if ok:
                # Flip horizontally — mirror effect for laptop webcam
                frame = cv2.flip(frame, 1)
                with self.lock:
                    self.frame = frame
            else:
                time.sleep(0.02)

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        if self.cap:
            self.cap.release()
        print("Shared camera stopped")


shared_camera = SharedCamera(0)  # 0 = default laptop webcam