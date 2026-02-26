import cv2
import threading
import time


class CameraHandler:
    def __init__(self, src=0, reconnect_interval=5.0, max_fail=20):
        self.src = src
        self.reconnect_interval = reconnect_interval
        self.max_fail = max_fail

        self.cap = None
        self.frame = None
        self.lock = threading.Lock()

        self.running = False
        self.thread = None
        self.fail_count = 0

    def _open(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None

        # Windows ưu tiên MSMF
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_MSMF)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)

        if self.cap.isOpened():
            print(f"[CAM] Camera {self.src} đã kết nối.")
            self.fail_count = 0
        else:
            print(f"[CAM] Không tìm thấy camera. Thử lại sau {self.reconnect_interval}s...")

    def start(self):
        if self.running:
            return

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
                self.fail_count = 0
            else:
                self.fail_count += 1

                if self.fail_count >= self.max_fail:
                    print("[CAM] Reset camera do lỗi liên tiếp")
                    self._open()
                    self.fail_count = 0

                time.sleep(0.1)

            time.sleep(0.01)

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return True, self.frame.copy()

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass