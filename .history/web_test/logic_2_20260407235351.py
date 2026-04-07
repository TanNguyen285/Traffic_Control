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
        """
        Hàm điều phối chính: Thu thập dữ liệu -> Tính toán -> Thực thi
        """
        # 1. XỬ LÝ RUN1 (LỆNH ƯU TIÊN XẢ TRẠM TỪ UI)
        if self.bien_run1:
            self.bien_run1 = False
            self.uart.send("m2")
            return {"status": "force_m2"}, "m2"

        # 2. KIỂM TRA LỆNH CHO PHÉP CHẠY TỪ ĐIỀU KHIỂN (ESP32)
        if not self.bien_run:
            return None, None
        self.bien_run = False

        # 3. THU THẬP DỮ LIỆU LOCAL (CAMERA & AI)
        if not self.module_chup_anh(selected_image):
            return {"error": "No Frame"}, "m0"

        # Chạy AI nội bộ
        self.ket_local = self.module_chay_cnn()
        if not self.ket_local:
            self.xe_local = self.module_chay_yolo()
        else:
            self.xe_local = 0
            # Giả lập kết quả yolo trống khi kẹt để tránh lỗi UI
            self.yolo_results = {
                "yolo_image": self._to_base64_url(self.frame_yolo) if hasattr(self, '_to_base64_url') else None, 
                "counts": [0,0,0,0,0]
            }

        # 4. ĐỒNG BỘ MẠNG (LẤY DỮ LIỆU TRẠM ĐỐI DIỆN)
        remote_connected = False
        ket_remote, xe_remote = False, 0 # Mặc định nếu mất kết nối

        try:
            self.eth.send_data(self.ket_local, self.xe_local)
            response = self.eth.get_remote_status()
            
            if response is not None and isinstance(response, dict):
                ket_remote = response.get('ket', False)
                xe_remote = response.get('xe', 0)
                remote_connected = True
        except Exception as e:
            print(f"[CẢNH BÁO] Mất kết nối trạm đối diện: {e}")

        # 5. TÍNH TOÁN LOGIC QUYẾT ĐỊNH
        cmd = self._tinh_toan_logic_dieu_khien(self.ket_local, self.xe_local, ket_remote, xe_remote)

        # 6. THỰC THI GỬI LỆNH XUỐNG PHẦN CỨNG
        self.uart.send(cmd)

        # 7. ĐÓNG GÓI KẾT QUẢ HIỂN THỊ
        result = self._dong_goi_ket_qua_hien_thi(remote_connected, ket_remote, xe_remote, cmd)
        
        return result, cmd

    # ==========================================
    # KHỐI LOGIC XỬ LÝ (THE BRAIN)
    # ==========================================
    def _tinh_toan_logic_dieu_khien(self, ket_local, xe_local, ket_remote, xe_remote):
        """Tách riêng phần tư duy để dễ bảo trì"""
        # Phân vai A/B dựa trên ID của trạm
        if self.id == 'TRAM_A':
            A, a = ket_local, not ket_local
            B, b = ket_remote, not ket_remote
            xe_a, xe_b = xe_local, xe_remote
        else: # TRAM_B
            B, b = ket_local, not ket_local
            A, a = ket_remote, not ket_remote
            xe_b, xe_a = xe_local, xe_remote

        # Thuật toán phân xử
        cmd = "m1"
        if A and (B or b):
            cmd = "A"  # Ưu tiên giải tỏa Trạm A nếu A kẹt
        elif B and a:
            cmd = "B"  # Nếu B kẹt và A thoáng, nhường cho B
        elif a and b:
            # Cả hai đều thoáng, chạy theo số lượng xe lớn nhất
            xe_max = max(xe_a, xe_b)
            cmd = self._esp32_mode(xe_max) if hasattr(self, '_esp32_mode') else "m1"
            
        return cmd

    # ==========================================
    # KHỐI DỮ LIỆU KẾT QUẢ (DATA FORMATTER)
    # ==========================================
    def _dong_goi_ket_qua_hien_thi(self, remote_connected, ket_remote, xe_remote, cmd):
        """Chuẩn bị dữ liệu để đẩy lên UI"""
        return {
            "cnn_status": "Ket Xe" if self.ket_local else "Thoang",
            "xe_local": self.xe_local,
            "xe_remote": xe_remote,
            "remote_jam": ket_remote,
            "remote_connected": remote_connected,
            "brightness": round(self.brightness, 2),
            "counts": self.yolo_results.get("counts", [0, 0, 0, 0, 0]),
            "input_image": self._to_base64_url(self.frame_raw) if hasattr(self, '_to_base64_url') else None, 
            "yolo_image": self.yolo_results.get('yolo_image'),
            "final_cmd": cmd
        }