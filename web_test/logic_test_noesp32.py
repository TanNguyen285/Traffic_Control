import time
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

        # TRIGGER ẢO (Dùng cho testing)
        self.bien_run = False   
        self.bien_run1 = False  
        self.last_test_time = time.time()

        # TRẠNG THÁI
        self.frame_raw = None 
        self.frame_cnn = None 
        self.frame_yolo = None 
        self.brightness = 0
        self.ket_local = False
        self.xe_local = 0
        self.yolo_results = {"counts": [0,0,0,0,0], "yolo_image": None}

    # ==========================================
    # GIẢ LẬP TÍN HIỆU TỪ ESP32 SAU MỖI 5 GIÂY
    # ==========================================
    def auto_trigger_test(self):
        current_time = time.time()
        # Cứ mỗi 10 giây giả lập run (AI bình thường), mỗi 30 giây giả lập run1 (Xả trạm)
        if current_time - self.last_test_time > 10:
            print(f"\n[TEST] --- Tự động kích hoạt: RUN (AI Scan) tại {self.id} ---")
            self.bien_run = True
            self.last_test_time = current_time
            
        # Bạn có thể uncomment nếu muốn test xả trạm tự động
        # if int(current_time) % 30 == 0: self.bien_run1 = True

    # ==========================================
    # KHỐI XỬ LÝ ETHERNET (CÓ LOG CHI TIẾT)
    # ==========================================
    def _sync_ethernet(self):
        remote_connected = False
        ket_remote, xe_remote = False, 0
        
        print(f"--- [ETHERNET SYNC START] ---")
        start_sync = time.perf_counter()
        
        try:
            # Gửi dữ liệu đi
            send_payload = {"ket": self.ket_local, "xe": self.xe_local}
            print(f"[SEND] {self.id} -> Remote: {send_payload}")
            self.eth.send_data(self.ket_local, self.xe_local)
            
            # Nhận dữ liệu về
            response = self.eth.get_remote_status() 
            
            if response and isinstance(response, dict):
                ket_remote = response.get('ket', False)
                xe_remote = response.get('xe', 0)
                remote_connected = True
                duration = (time.perf_counter() - start_sync) * 1000
                print(f"[RECV] {self.id} <- Remote: {response} (Time: {duration:.2f}ms)")
            else:
                print(f"[WARN] {self.id}: Nhận dữ liệu rỗng hoặc sai định dạng")
        except Exception as e:
            print(f"[OFFLINE] {self.id}: Không kết nối được trạm đối diện. Lỗi: {e}")
            print(f"[MODE] Chạy độc lập (Standalone)")

        return remote_connected, ket_remote, xe_remote

    # ==========================================
    # THỰC THI CHÍNH
    # ==========================================
    def thuc_thi_AI(self):
        # 0. Tự kích hoạt biến chạy nếu đang test
        self.auto_trigger_test()

        if not self.bien_run and not self.bien_run1:
            return None, None
        
        # 1. CHỤP ẢNH
        if self.frame_raw is None or self.bien_run:
            if not self.module_chup_anh():
                return {"error": "No Frame"}, "m0"
            self.ket_local = self.module_chay_cnn()
        
        self.bien_run = False 

        # 2. VÒNG LẶP KẸT XE
        while self.ket_local:
            if self.bien_run1: break 
            if self.module_chup_anh(): 
                self.ket_local = self.module_chay_cnn()
            print(f"[{self.id}] Đang kẹt xe... Chờ thông thoáng...")
            time.sleep(0.5)

        # 3. SAU KHI THOÁT KẸT
        if self.bien_run1:
            self.bien_run1 = False
            self.ket_local = False
            cmd_final = "m2"
        else:
            self.xe_local = self.module_chay_yolo()
            cmd_final = None 

        # 4. ĐỒNG BỘ ETHERNET & TÍNH TOÁN
        remote_conn, ket_rem, xe_rem = self._sync_ethernet()

        if cmd_final is None:
            cmd_final = self.logic_dieu_khien(
                self.ket_local, self.xe_local, 
                ket_rem, xe_rem, 
                remote_conn
            )

        # 5. PHẢN HỒI
        print(f"[RESULT] Quyết định cuối cùng: {cmd_final}")
        # self.uart.send(cmd_final) # Tạm đóng nếu không có ESP32 thật

        return self.result_AI(remote_conn, ket_rem, xe_rem, cmd_final), cmd_final

    # --- Các hàm bổ trợ giữ nguyên từ code của bạn ---
    def module_chup_anh(self):
        ret, frame = self.cam.read()
        if not ret or frame is None: return False
        self.frame_raw = frame
        self.frame_cnn, self.frame_yolo, self.brightness = self.pre_proc.input_yolo_cnn(frame, skip_roi=False)
        return True

    def module_chay_cnn(self):
        if self.frame_cnn is None: return False
        status_local, conf, _ = self.cnn.predict(self.frame_cnn)
        self.ket_local = (status_local == "Ket Xe")
        return self.ket_local

    def module_chay_yolo(self):
        if self.frame_yolo is None: return 0
        self.yolo_results, self.xe_local = self.ai.detect(self.frame_yolo, self.brightness)
        return self.xe_local

    def logic_dieu_khien(self, ket_local, xe_local, ket_remote, xe_remote, remote_connected):
        if not remote_connected:
            return "A" if (ket_local and self.id == 'TRAM_A') else "m1"
        # ... (logic phối hợp giữ nguyên)
        return "m1"