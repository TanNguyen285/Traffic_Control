import cv2
import threading
import time
import platform # Để nhận diện hệ điều hành

class Camera:
    def __init__(self, src=0, reconnect_interval=10.0, max_fail=20):
        self.src = src
        self.reconnect_interval = reconnect_interval
        self.max_fail = max_fail

        self.cap = None
        self.frame = None
        self.lock = threading.Lock()

        self.running = False
        self.thread = None
        self.fail_count = 0
        
        # Kích thước chuẩn cho YOLO
        self.width = 640
        self.height = 480

    def _open(self):
        """Thiết lập kết nối tối ưu cho từng hệ điều hành"""
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None

        system_name = platform.system()
        
        if system_name == "Windows":
            # Ưu tiên MSMF hoặc DSHOW trên Windows
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_MSMF)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
        
        elif system_name == "Linux":
            # Trên Raspberry Pi dùng V4L2 là chuẩn nhất cho OpenCV
            # Nếu dùng Camera CSI (Pi Cam v2/v3), đảm bảo đã bật legacy camera hoặc dùng libcamera-v4l2
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
            
            # Tối ưu cho Rasp: Thiết lập định dạng nén MJPG để lấy FPS cao hơn
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        else:
            self.cap = cv2.VideoCapture(self.src)

        if self.cap.isOpened():
            # Cài đặt độ phân giải
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Gợi ý cho Rasp: Giảm buffer xuống 1 để ảnh luôn là mới nhất (Realtime)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            print(f"[CAM] {system_name} - Camera {self.src} kết nối. Độ phân giải: {actual_w}x{actual_h}")
            self.fail_count = 0
        else:
            print(f"[CAM] Không tìm thấy camera {self.src}. Thử lại sau {self.reconnect_interval}s...")

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
                # --- THÊM LOGIC CẮT ẢNH Ở ĐÂY ---
                h, w = frame.shape[:2]
                if w > self.width or h > self.height:
                    # Tính toán tọa độ để cắt chính giữa
                    left = (w - self.width) // 2
                    top = (h - self.height) // 2
                    right = left + self.width
                    bottom = top + self.height
                    
                    # Crop ảnh
                    frame = frame[top:bottom, left:right]
                    print(f"[CAM] Ảnh gốc {w}x{h} đã được cắt về {self.width}x{self.height}.")
                # -------------------------------

                with self.lock:
                    self.frame = frame
                self.fail_count = 0
            else:
                self.fail_count += 1
                if self.fail_count >= self.max_fail:
                    print("[CAM] Lỗi liên tiếp, đang reset camera...")
                    self._open()
                    self.fail_count = 0
                time.sleep(1)

            # Trên Pi 5, bạn có thể để sleep thấp hơn (0.01) để lấy 30-60 FPS
            time.sleep(0.05) 

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return True, self.frame.copy()

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
            print("[CAM] Đã đóng camera.")