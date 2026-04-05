import cv2
import threading
import time

class Camera:
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
        
        # Thiết lập kích thước mong muốn (Khớp với YOLO)
        self.width = 640
        self.height = 640

    def _open(self):
        """Thiết lập kết nối và cấu hình phần cứng Camera"""
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None

        # Thử mở camera với các driver khác nhau (Windows)
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_MSMF)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)

        if self.cap.isOpened():
            # --- CÀI ĐẶT ĐỘ PHÂN GIẢI TRỰC TIẾP TỪ PHẦN CỨNG ---
            # 3: CAP_PROP_FRAME_WIDTH, 4: CAP_PROP_FRAME_HEIGHT
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Kiểm tra lại xem camera có hỗ trợ đúng 640x640 không
            actual_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            print(f"[CAM] Camera {self.src} kết nối thành công. Độ phân giải: {actual_w}x{actual_h}")
            self.fail_count = 0
        else:
            print(f"[CAM] Không tìm thấy camera {self.src}. Thử lại sau {self.reconnect_interval}s...")

    def start(self):
        """Khởi chạy luồng đọc camera"""
        if self.running:
            return

        self.running = True
        self._open()
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        """Luồng chạy ngầm: Chỉ làm nhiệm vụ lấy ảnh nhanh nhất có thể"""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self._open()
                time.sleep(self.reconnect_interval)
                continue

            ret, frame = self.cap.read()

            if ret and frame is not None:
                with self.lock:
                    # TỐI ƯU: Ở đây chỉ gán tham chiếu, không dùng .copy() để đỡ tốn CPU
                    self.frame = frame
                self.fail_count = 0
            else:
                self.fail_count += 1
                if self.fail_count >= self.max_fail:
                    print("[CAM] Lỗi liên tiếp, đang reset camera...")
                    self._open()
                    self.fail_count = 0
                time.sleep(0.1)

            # Nghỉ cực ngắn để luồng khác có thể giành quyền (Lock)
            time.sleep(0.03)#FPS ~30

    def read(self):
        """Hàm lấy ảnh dành cho AI xử lý: Trả về bản copy để an toàn"""
        with self.lock:
            if self.frame is None:
                return False, None
            # TỐI ƯU: Chỉ copy tại đây để đảm bảo ảnh đưa sang AI không bị thay đổi 
            # bởi luồng _reader đang chạy song song.
            return True, self.frame.copy()

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def stop(self):
        """Dừng camera và giải phóng tài nguyên"""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)

        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            print("[CAM] Đã đóng camera.")