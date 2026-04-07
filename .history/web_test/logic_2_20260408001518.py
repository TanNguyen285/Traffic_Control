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
    
    # ==========================================
    # KHỐI 4: ĐIỀU PHỐI LOGIC CHÍNH (Đã sửa)
    # ==========================================
    def thuc_thi_AI(self, selected_image=None):
        # 1. XỬ LÝ RUN1 (LỆNH ƯU TIÊN XẢ TRẠM TỪ UI)
        if self.bien_run1:
            self.bien_run1 = False
            self.uart.send("m2")
            return {"status": "force_m2"}, "m2"

        # 2. KIỂM TRA LỆNH CHO PHÉP CHẠY TỪ ĐIỀU KHIỂN (ESP32)
        if not self.bien_run:
            return None, None
        self.bien_run = False

        # 3. THU THẬP DỮ LIỆU LOCAL
        if not self.module_chup_anh(selected_image):
            return {"error": "No Frame"}, "m0"

        self.ket_local = self.module_chay_cnn()
        if not self.ket_local:
            self.xe_local = self.module_chay_yolo()
        else:
            self.xe_local = 0
            self.yolo_results = {
                "yolo_image": self._to_base64_url(self.frame_yolo) if hasattr(self, '_to_base64_url') else None, 
                "counts": [0,0,0,0,0]
            }

        # 4. ĐỒNG BỘ MẠNG (Xử lý để không bị treo khi mất mạng)
        remote_connected = False
        ket_remote, xe_remote = False, 0 

        try:
            # Gửi data đi
            self.eth.send_data(self.ket_local, self.xe_local)
            # Thử lấy data về
            response = self.eth.get_remote_status()
            
            if response is not None and isinstance(response, dict):
                ket_remote = response.get('ket', False)
                xe_remote = response.get('xe', 0)
                remote_connected = True
        except Exception as e:
            # Nếu mất kết nối, remote_connected vẫn là False, code vẫn chạy tiếp
            print(f"[CẢNH BÁO] Chế độ độc lập (Mất mạng): {e}")

        # 5. TÍNH TOÁN LOGIC QUYẾT ĐỊNH (Truyền thêm remote_connected)
        cmd = self.logic_dieu_khien(self.ket_local, self.xe_local, ket_remote, xe_remote, remote_connected)

        # 6. THỰC THI GỬI LỆNH
        self.uart.send(cmd)

        # 7. ĐÓNG GÓI KẾT QUẢ
        result = self._dong_goi_ket_qua_hien_thi(remote_connected, ket_remote, xe_remote, cmd)
        return result, cmd

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