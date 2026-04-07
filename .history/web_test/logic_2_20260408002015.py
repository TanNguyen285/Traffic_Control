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
        Logic: Nếu kẹt (A), im lặng chạy AI liên tục cho đến khi 
        thoáng (a) hoặc có biến run1 thì mới gửi lệnh và thoát.
        """
        # 1. KIỂM TRA TRIGGER BAN ĐẦU
        if not self.bien_run and not self.bien_run1:
            return None, None
        
        # Lưu lại trạng thái ban đầu để biết có cần vào vòng lặp kẹt không
        # Nếu chưa có ảnh thì phải chụp lần đầu để kiểm tra
        if self.frame_raw is None or self.bien_run:
            if not self.module_chup_anh(selected_image):
                return {"error": "No Frame"}, "m0"
            self.ket_local = self.module_chay_cnn()

        self.bien_run = False # Reset trigger

        # 2. KHỐI XỬ LÝ VÒNG LẶP KẸT XE (IM LẶNG)
        # Nếu CNN báo kẹt (A), bắt đầu vòng lặp "quét ngầm"
        while self.ket_local:
            # Kiểm tra lệnh xả trạm (run1) để thoát khẩn cấp
            if self.bien_run1:
                break 
            
            # Chụp ảnh và quét lại CNN liên tục (Không gửi UART/ETH ở đây)
            if self.module_chup_anh(selected_image):
                self.ket_local = self.module_chay_cnn()
            
            # Tùy chọn: Nghỉ 100ms để tránh treo CPU vì vòng lặp quá nhanh
            # import time; time.sleep(0.1)

        # 3. KHI THOÁT KHỎI VÒNG LẶP (Có 2 trường hợp: Hết kẹt hoặc bị ép bởi run1)
        
        # Nếu thoát do run1 (Xả trạm)
        if self.bien_run1:
            self.bien_run1 = False
            self.ket_local = False # Coi như hết kẹt để cập nhật UI
            cmd_final = "m2"
        else:
            # Nếu thoát do Hết kẹt (a) -> Chạy nốt YOLO để đếm xe lần cuối
            self.xe_local = self.module_chay_yolo()
            cmd_final = None # Sẽ tính toán ở bước dưới

        # 4. ĐỒNG BỘ MẠNG VÀ TÍNH TOÁN LỆNH CUỐI CÙNG
        remote_connected = False
        ket_remote, xe_remote = False, 0 

        try:
            # Chỉ gửi và nhận dữ liệu 1 LẦN DUY NHẤT sau khi đã thoát kẹt
            self.eth.send_data(self.ket_local, self.xe_local)
            response = self.eth.get_remote_status()
            if isinstance(response, dict):
                ket_remote = response.get('ket', False)
                xe_remote = response.get('xe', 0)
                remote_connected = True
        except:
            print("[CẢNH BÁO] Chế độ độc lập")

        # Nếu chưa có lệnh từ run1 thì mới tính logic phối hợp
        if cmd_final is None:
            cmd_final = self.logic_dieu_khien(
                self.ket_local, self.xe_local, 
                ket_remote, xe_remote, 
                remote_connected
            )

        # 5. GỬI LỆNH XUỐNG ESP32 (CHỈ GỬI 1 LẦN SAU CÙNG)
        self.uart.send(cmd_final)

        # 6. TRẢ KẾT QUẢ HIỂN THỊ
        result = self._dong_goi_ket_qua_hien_thi(remote_connected, ket_remote, xe_remote, cmd_final)
        return result, cmd_final
    # ==========================================
    # KHỐI LOGIC XỬ LÝ (Đã sửa để chạy độc lập)
    # ==========================================
    def logic_dieu_khien(self, ket_local, xe_local, ket_remote, xe_remote, remote_connected):
        """
        Nếu remote_connected = False: Trạm tự quyết định dựa trên mắt nó thấy.
        Nếu remote_connected = True: Trạm phối hợp với trạm đối diện.
        """
        
        # --- TRƯỜNG HỢP MẤT KẾT NỐI (CHẠY ĐỘC LẬP) ---
        if not remote_connected:
            if ket_local:
                # Nếu mình kẹt, ép xanh hướng mình (A hoặc B tùy ID)
                return "A" if self.id == 'TRAM_A' else "B"
            else:
                # Nếu thoáng, chạy theo số xe mình đếm được
                return self._esp32_mode(xe_local) if hasattr(self, '_esp32_mode') else "m1"

        # --- TRƯỜNG HỢP CÓ KẾT NỐI (CHẠY PHỐI HỢP) ---
        if self.id == 'TRAM_A':
            A, a = ket_local, not ket_local
            B, b = ket_remote, not ket_remote
            xe_a, xe_b = xe_local, xe_remote
        else: # TRAM_B
            B, b = ket_local, not ket_local
            A, a = ket_remote, not ket_remote
            xe_b, xe_a = xe_local, xe_remote

        cmd = "m1"
        if A and (B or b):
            cmd = "A"  
        elif B and a:
            cmd = "B"  
        elif a and b:
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