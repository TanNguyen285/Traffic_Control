import cv2
import base64
import sys

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, eth_service, station_id='Tram_A'):
        
        self.ai = yolo_ai            
        self.cnn = cnn_service      
        self.pre_proc = pre_proc    
        self.uart = uart
        self.cam = cam
        self.eth = eth_service 
        self.id = station_id.upper()

        # TRIGGER TỪ ESP32
        self.bien_run = False   # Chạy AI bình thường
        self.bien_run1 = False  # Xả trạm (m2)

        # CÁC BIẾN LƯU TRỮ TRẠNG THÁI (Để các khối dùng chung)
        self.frame_raw = None # frame gốc lấy từ camera, chưa qua xử lý gì
        self.frame_cnn = None # frame cho CNN
        self.frame_yolo = None # frame cho YOLO
        self.brightness = 0
        
        # Đã đổi is_local_jam thành ket_local
        self.ket_local = False
        self.xe_local = 0
        self.yolo_results = {"counts": [0,0,0,0,0], "yolo_image": None}

    # ==========================================
    # CALLBACK TỪ UART
    # ==========================================
    def uart_esp32_rasp(self, signal="run"):
        if signal == "run1":
            self.bien_run1 = True
        else:
            self.bien_run = True

    # ==========================================
    # KHỐI 1: LẤY ẢNH VÀ TIỀN XỬ LÝ
    # ==========================================
    def module_chup_anh(self, selected_image=None):
        """Chỉ làm nhiệm vụ lấy ảnh và cắt/resize cho model"""
        is_upload = selected_image is not None
        frame = selected_image if is_upload else self.cam.read()[1]
        
        if frame is None:
            return False
            
        self.frame_raw = frame
        self.frame_cnn, self.frame_yolo, self.brightness = \
            self.pre_proc.input_yolo_cnn(frame, skip_roi=is_upload)
        return True

    # ==========================================
    # KHỐI 2: CHẠY CNN (Nhận diện kẹt)
    # ==========================================
    def module_chay_cnn(self):
        """Chỉ chạy CNN. Trả về True nếu kẹt xe"""
        if self.frame_cnn is None: return False
        
        status_local, _, _ = self.cnn.predict(self.frame_cnn)
        self.ket_local = (status_local == "Ket Xe")
        return self.ket_local

    # ==========================================
    # KHỐI 3: CHẠY YOLO (Đếm xe)
    # ==========================================
    def module_chay_yolo(self):
        """Chỉ chạy YOLO. Lưu và trả về số lượng xe"""
        if self.frame_yolo is None: return 0
        
        self.yolo_results, self.xe_local = self.ai.detect(self.frame_yolo, self.brightness)
        return self.xe_local

    # ==========================================
    # KHỐI 4: ĐIỀU PHỐI LOGIC CHÍNH
    # ==========================================
    def thuc_thi_AI(self, selected_image=None):
        # 1. XỬ LÝ RUN1 (XẢ TRẠM)
        if self.bien_run1:
            self.bien_run1 = False
            self.uart.send("m2")
            return {"status": "force_m2"}, "m2"

        # 2. CHỜ LỆNH RUN TỪ ESP32
        if not self.bien_run:
            return None, None
        self.bien_run = False

        # --- BƯỚC THU THẬP DỮ LIỆU (CHẠY AI 1 LẦN DUY NHẤT) ---
        if not self.module_chup_anh(selected_image):
            return {"error": "No Frame"}, "m0"

        # Chạy AI để lấy dữ liệu hiện tại của trạm mình
        self.ket_local = self.module_chay_cnn()
        
        if not self.ket_local:
            self.xe_local = self.module_chay_yolo()
        else:
            self.xe_local = 0
            # Giả lập kết quả yolo trống khi kẹt để UI không bị lỗi
            self.yolo_results = {"yolo_image": self._to_base64_url(self.frame_yolo) if hasattr(self, '_to_base64_url') else None, "counts": [0,0,0,0,0]}

        # ==========================================
        # ĐỒNG BỘ MẠNG (CÓ BẢO VỆ CHỐNG MẤT KẾT NỐI)
        # ==========================================
        remote_connected = False
        remote_data = {}

        try:
            # Gửi dữ liệu đi và cố gắng lấy dữ liệu về
            self.eth.send_data(self.ket_local, self.xe_local)
            response = self.eth.get_remote_status()
            
            # Kiểm tra xem có nhận được data thật không
            if response is not None and isinstance(response, dict):
                remote_data = response
                remote_connected = True
        except Exception as e:
            # Nếu đứt cáp, mất wifi, trạm kia sập nguồn -> Bỏ qua lỗi, không làm crash Pi
            print(f"[CẢNH BÁO] Mất kết nối trạm đối diện: {e}")

        # Nếu mất kết nối, biến tự động fallback về: Không kẹt (False) và 0 xe.
        ket_remote = remote_data.get('ket', False)
        xe_remote = remote_data.get('xe', 0)
        
        # --- LOGIC A/a B/b (NHÂN BẢN) ---
        # Gán trực tiếp biến không cần tạo thêm biến trung gian nữa
        if self.id == 'TRAM_A':
            A, a = self.ket_local, not self.ket_local
            B, b = ket_remote, not ket_remote
            xe_a, xe_b = self.xe_local, xe_remote
        else: # TRAM_B
            B, b = self.ket_local, not self.ket_local
            A, a = ket_remote, not ket_remote
            xe_b, xe_a = self.xe_local, xe_remote

        # PHÂN XỬ LỆNH (Chỉ dùng kết quả AI đã có, không chạy lại AI)
        cmd = "m1"
        if A and (B or b):
            cmd = "A" # Ưu tiên giải tỏa Trạm A nếu A kẹt
        elif B and a:
            cmd = "B" # Nếu B kẹt và A thoáng, nhường cho B (Gửi lệnh B)
        elif a and b:
            # Cả hai đều thoáng, chạy theo số lượng xe
            xe_max = max(xe_a, xe_b)
            # Giả định bạn có hàm _esp32_mode() để convert số xe ra m1, m2...
            cmd = self._esp32_mode(xe_max) if hasattr(self, '_esp32_mode') else "m1"

        # GỬI LỆNH XUỐNG ESP32
        self.uart.send(cmd)

        # Trả kết quả hiển thị lên màn hình
        result = {
            "cnn_status": "Ket Xe" if self.ket_local else "Thoang",
            "xe_local": self.xe_local,
            "xe_remote": xe_remote,
            "remote_jam": ket_remote,
            "remote_connected": remote_connected,  # <--- BẠN THÊM DÒNG NÀY VÀO NHÉ
            "brightness": round(self.brightness, 2),
            "counts": self.yolo_results.get("counts", [0, 0, 0, 0, 0]),
            "input_image": self._to_base64_url(self.frame_raw) if hasattr(self, '_to_base64_url') else None, 
            "yolo_image": self.yolo_results.get('yolo_image')
        }
        return result, cmd