import os
import time
import cv2
import base64
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, eth_service, station_id='TRAM_A'):
            self.ai = yolo_ai            
            self.cnn = cnn_service      
            self.pre_proc = pre_proc    
            self.uart = uart
            self.cam = cam
            self.eth = eth_service 
            self.id = station_id.upper()

            # --- TRẠNG THÁI TRIGGER ---
            self.bien_run = False   
            self.bien_run1 = False  
            
            # --- CHẾ ĐỘ HOẠT ĐỘNG ---
            self.operation_mode = "single"  # "single" hoặc "branch"
            
            # --- QUẢN LÝ GIẢ LẬP TỰ ĐỘNG ---
            self.auto_mode = True 
            self.last_run_time = time.time()
            self.last_run1_time = time.time()
            
            # Cấu hình chu kỳ (giây)
            self.INTERVAL_RUN = 10   # Cứ 10 giây tự quét AI một lần
            self.INTERVAL_RUN1 = 25  # Cứ 25 giây tự xả trạm một lần

            # --- CÁC BIẾN TRẠNG THÁI ---
            self.frame_raw = None 
            self.frame_cnn = None 
            self.frame_yolo = None 
            self.brightness = 0
            self.ket_local = False
            self.xe_local = 0
            self.yolo_results = {"counts": [0,0,0,0,0], "yolo_image": None}


    def set_mode(self, mode):
            """Đổi chế độ hoạt động: 'single' hoặc 'branch'"""
            if mode not in ['single', 'branch']:
                print(f"[MODE] Chế độ không hợp lệ: {mode}")
                return False
            
            self.operation_mode = mode
            print(f"[MODE] Chế độ hoạt động thay đổi: {mode}")
            
            if mode == "branch":
                print("[MODE] ⚠️  Chế độ Nhánh: Cần Ethernet. Nếu không có kết nối sẽ không chạy")
            else:
                print("[MODE] ✅ Chế độ Đơn: Hoạt động độc lập không cần Ethernet")
            
            return True


    def uart_esp32_rasp(self, signal="run"):
            """Hàm nhận tín hiệu từ UART"""
            if signal == "run1":
                self.bien_run1 = True
                print("[UART] Nhận lệnh xả trạm (run1)")
            else:
                self.bien_run = True
                print("[UART] Nhận lệnh quét AI (run)")

        # ==========================================
        # BỘ TỰ ĐỘNG PHÁT TÍN HIỆU (MÃ GIẢ)
        # ==========================================
    def _auto_generator(self):
            """Hàm này tự động bật các biến trigger theo thời gian thực"""
            current_time = time.time()
            
            # Tự động bật run (Quét AI)
            if current_time - self.last_run_time > self.INTERVAL_RUN:
                print(f"\n[AUTO-TRIGGER] Kích hoạt RUN (AI Scan) sau {self.INTERVAL_RUN}s")
                self.bien_run = True
                self.last_run_time = current_time

            # Tự động bật run1 (Xả trạm)
            if current_time - self.last_run1_time > self.INTERVAL_RUN1:
                print(f"\n[AUTO-TRIGGER] Kích hoạt RUN1 (Xả trạm) sau {self.INTERVAL_RUN1}s")
                self.bien_run1 = True
                self.last_run1_time = current_time

        # ==========================================
        # KHỐI 1: LẤY ẢNH VÀ TIỀN XỬ LÝ
        # ==========================================
    def module_chup_anh(self):
            ret, frame = self.cam.read()
            if not ret or frame is None:
                return False
            self.frame_raw = frame
            self.frame_cnn, self.frame_yolo, self.brightness = \
                self.pre_proc.input_yolo_cnn(frame, skip_roi=False)
            return True


  
        # ==========================================
        # KHỐI 2: CHẠY CNN (Nhận diện kẹt)
        # ==========================================
    def module_chay_cnn(self):
        if self.frame_cnn is None: return False
        status_local, conf, _ = self.cnn.predict(self.frame_cnn)
        self.ket_local = (status_local == "Ket Xe")
        
        # Vẽ kết quả lên ảnh
        self.frame_raw = self.cnn.draw_prediction(self.frame_raw, status_local, conf)
        
        # --- LƯU ĐÈ ẢNH GỐC ---
        path_input = os.path.join(BASE_DIR, "static", "current_input.jpg")
        cv2.imwrite(path_input, self.frame_raw)
        print(f"--- Đang lưu ảnh vào: {os.path.abspath(path_input)}")
        return self.ket_local
        # ==========================================
        # KHỐI 3: CHẠY YOLO (Đếm xe)
        # ==========================================
    def module_chay_yolo(self):
            if self.frame_yolo is None: return 0
            self.yolo_results, self.xe_local = self.ai.detect(self.frame_yolo, self.brightness)
            path_yolo = os.path.join(BASE_DIR, "static", "current_yolo.jpg")
            cv2.imwrite(path_yolo, self.yolo_results['frame'])
            print(f"--- Đang lưu ảnh vào: {os.path.abspath(path_yolo)}")
            return self.xe_local

        # ==========================================
        # KHỐI 4: ĐIỀU PHỐI LOGIC CHÍNH
        # ==========================================
    def thuc_thi_AI(self):
            # TỰ ĐỘNG CẬP NHẬT TRIGGER NẾU ĐANG Ở CHẾ ĐỘ GIẢ LẬP
            if self.auto_mode:
                self._auto_generator()

            # 1. KIỂM TRA TRIGGER
            if not self.bien_run and not self.bien_run1:
                return None, None
            
            # === CHẾ ĐỘ "BRANCH" - KIỂM TRA ETHERNET ===
            if self.operation_mode == "branch":
                try:
                    response = self.eth.get_remote_status()
                    if not isinstance(response, dict) or response == {'ket': False, 'xe': 0}:
                        # Chưa có kết nối hoặc chỉ có dữ liệu default
                        print("[MODE] ⚠️  Chế độ Nhánh: Chưa kết nối được Ethernet, không chạy")
                        return None, None
                except:
                    print("[MODE] ⚠️  Chế độ Nhánh: Lỗi kiểm tra Ethernet, không chạy")
                    return None, None
            
            print(f"[{self.id}] Bắt đầu chu trình AI...")

            # 2. CHỤP ẢNH & KIỂM TRA KẸT LẦN ĐẦU
            if self.module_chup_anh():
                self.ket_local = self.module_chay_cnn()
            
            self.bien_run = False 

            # 3. VÒNG LẶP KẸT XE (IM LẶNG)
            while self.ket_local:
                # Nếu trong lúc kẹt mà có lệnh xả trạm (run1) thì thoát ngay
                if self.bien_run1:
                    break 
                
                print(f"[{self.id}] Đang kẹt xe... Chờ thông thoáng...")
                if self.module_chup_anh(): 
                    self.ket_local = self.module_chay_cnn()
                
                time.sleep(1) # Nghỉ để tránh quá tải CPU

            # 4. SAU KHI THOÁT KẸT
            if self.bien_run1:
                print(f"[{self.id}] Tín hiệu Xả trạm kích hoạt!")
                self.bien_run1 = False
                self.ket_local = False 
                cmd_final = "m2"
            else:
                print(f"[{self.id}] Đường thoáng, đang đếm xe...")
                self.xe_local = self.module_chay_yolo()
                cmd_final = None 

            # 5. ĐỒNG BỘ MẠNG
            remote_connected, ket_remote, xe_remote = self._sync_ethernet()

            # 6. TÍNH TOÁN LỆNH CUỐI
            if cmd_final is None:
                cmd_final = self.logic_dieu_khien(
                    self.ket_local, self.xe_local, 
                    ket_remote, xe_remote, 
                    remote_connected
                )

            # 7. PHẢN HỒI
            print(f"[RESULT] Quyết định: {cmd_final}")
            # self.uart.send(cmd_final) # Mở ra nếu muốn gửi thật xuống ESP32

            result = self.result_AI(remote_connected, ket_remote, xe_remote, cmd_final)
            return result, cmd_final


    def _sync_ethernet(self):
            """Hàm hỗ trợ đồng bộ Ethernet"""
            conn, k_rem, x_rem = False, False, 0
            try:
                self.eth.send_data(self.ket_local, self.xe_local)
                response = self.eth.get_remote_status()
                if isinstance(response, dict):
                    k_rem = response.get('ket', False)
                    x_rem = response.get('xe', 0)
                    conn = True
            except:
                pass
            return conn, k_rem, x_rem

    def _esp32_mode(self, xe_count):
            """Hàm phụ trợ để phân mức lệnh dựa trên số lượng xe"""
            if xe_count < 2:
                return "m1"
            elif xe_count < 5:
                return "m2"
            elif xe_count < 8:
                return "m3"
            else:
                return "m4"

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
                    # Nếu thoáng, chạy theo số xe mình đếm được (phân mức m1-m4)
                    return self._esp32_mode(xe_local)

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
                # Ưu tiên hướng A nếu A kẹt (bất kể B thế nào)
                cmd = "A"  
            elif B and a:
                # Ưu tiên hướng B nếu B kẹt và A đang thoáng
                cmd = "B"  
            elif a and b:
                # Cả hai cùng thoáng: So sánh xe của cả 2 nhánh, lấy max để chọn mức m
                xe_max = max(xe_a, xe_b)
                cmd = self._esp32_mode(xe_max)
                
            return cmd

    def result_AI(self, remote_connected, ket_remote, xe_remote, cmd):
        """Chuẩn bị dữ liệu SIÊU NHẸ"""
        import time
        # Tạo mã version dựa trên miligiây để ép trình duyệt load ảnh mới
        v = int(time.time() * 1000) 
        
        return {
            "cnn_status": "Ket Xe" if self.ket_local else "Thoang",
            "xe_local": self.xe_local,
            "xe_remote": xe_remote,
            "remote_jam": ket_remote,
            "remote_connected": remote_connected,
            "brightness": round(self.brightness, 2),
            "counts": self.yolo_results.get("counts", [0, 0, 0, 0, 0]),
            
            # Gửi link file kèm token version v
            "input_image": f"/static/current_input.jpg?v={v}", 
            "yolo_image": f"/static/current_yolo.jpg?v={v}",
            "final_cmd": cmd
        }