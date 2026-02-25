import cv2
import threading
import time

class CameraHandler:
    def __init__(self, src=0, reconnect_interval=5.0):
        self.src = src
        self.reconnect_interval = reconnect_interval
        self.cap = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

    def _open(self):
        if self.cap is not None: self.cap.release()
        # Ưu tiên MSMF (Win 10+) sau đó mới tới DSHOW
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
        
        if self.cap.isOpened():
            print(f"[CAM] Camera {self.src} đã kết nối.")
        else:
            print(f"[CAM] Không tìm thấy camera. Thử lại sau {self.reconnect_interval}s...")

    def start(self):
        if self.running: return
        self.running = True
        self._open()
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self._open()
                time.sleep(self.reconnect_interval)
                continue
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.frame = frame.copy()
            else:
                time.sleep(0.5)
            time.sleep(0.01)

    def read(self):
        with self.lock:
            if self.frame is None: return False, None
            return True, self.frame.copy()

    def stop(self):
        self.running = False
        if self.cap: self.cap.release()