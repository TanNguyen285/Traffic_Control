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

    def _open(self):
        """Mở camera và thiết lập các thông số tối ưu hiệu năng nhất"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.cap = cv2.VideoCapture(self.src)
        
        if self.cap.isOpened():
            # TỐI ƯU HIỆU NĂNG:
            # 1. Ép buffer về 1 để xóa bỏ hoàn toàn độ trễ tích tụ (Lag)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 2. Tắt các tiến trình tính toán phụ của Driver nếu có thể (tùy camera)
            # self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            print(f"[CAM] Camera {self.src} connected. Buffer optimized.")
            self.fail_count = 0
        else:
            print(f"[CAM] Camera {self.src} connection failed!")

    def start(self):
        if self.running: return
        self.running = True
        self._open()
        # Daemon=True để luồng tự đóng khi chương trình chính thoát
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        """Luồng đọc 'thực dụng': Chỉ quan tâm đến khung hình mới nhất"""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self._open()
                time.sleep(self.reconnect_interval)
                continue

            # CHIẾN THUẬT 'GRAB-AND-GO':
            # grab() cực nhanh vì nó không giải mã (decode) ảnh.
            # Ta dùng nó để đẩy hết đống ảnh cũ trong buffer ra ngoài.
            if not self.cap.grab():
                self.fail_count += 1
                if self.fail_count >= self.max_fail:
                    self._open()
                continue
            
            # Chỉ retrieve (giải mã) đúng khung hình cuối cùng để tiết kiệm CPU
            ret, frame = self.cap.retrieve()

            if ret and frame is not None:
                with self.lock:
                    self.frame = frame
                self.fail_count = 0
            
            # Nghỉ 1ms để giải phóng CPU cho các luồng AI chạy
            time.sleep(0.001)

    def read(self):
        """Hàm trả về frame cho logic AI"""
        with self.lock:
            if self.frame is None:
                return False, None
            # Trả về bản copy để đảm bảo luồng reader không ghi đè dữ liệu 
            # khi AI đang xử lý dở dang mảng pixel này
            return True, self.frame.copy()

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            print("[CAM] Resources released.")