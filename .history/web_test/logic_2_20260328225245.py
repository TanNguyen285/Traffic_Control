import cv2
import base64
import time

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, eth_service, station_id='A',
                 t_m1=15, t_m2=20, t_m3=25, t_m4=40, t_ket=150, t_y=3):
        
        self.ai = yolo_ai            
        self.cnn = cnn_service      
        self.pre_proc = pre_proc    
        self.uart = uart
        self.cam = cam
        self.eth = eth_service 
        
        self.id = station_id.upper()
        
        # --- QUẢN LÝ TRẠNG THÁI KẸT ---
        self.is_jamming = False      # Đang trong trạng thái kẹt xe
        self.jam_start_time = 0      # Thời điểm bắt đầu kẹt
        self.last_relief_time = 0    # Thời điểm bắt đầu xả cứu trạm B (20s)
        self.in_relief_mode = False  # Đang trong 20s cứu trạm B
        
        self.t_ket_limit = 150       # Ngưỡng 150s để cứu trạm B
        self.t_relief = 20           # Thời gian cứu trạm B

        self.t_modes = {'m1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'A': t_ket}
        self.t_y = t_y

    def AI_CNN_SCI(self, selected_image=None):
        # 1. Lấy ảnh và Tiền xử lý
        frame_raw = selected_image if selected_image is not None else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        input_image_url = self._to_base64_url(frame_raw)
        frame_cnn, frame_yolo, brightness = self.pre_proc.input_yolo_cnn(frame_raw, skip_roi=(selected_image is not None))

        # 2. CNN LUÔN QUÉT LIÊN TỤC
        status_local, _, _ = self.cnn.predict(frame_cnn)
        is_jam_now = (status_local == "Ket Xe")
        
        curr_time = time.time()

        # 3. LOGIC XỬ LÝ KẸT (A)
        if is_jam_now:
            if not self.is_jamming:
                # Mới bắt đầu kẹt
                self.is_jamming = True
                self.jam_start_time = curr_time
                self.in_relief_mode = False
            
            # Kiểm tra xem đã kẹt quá 150s chưa để xả cứu trạm B
            elapsed_jam = curr_time - self.jam_start_time
            
            if not self.in_relief_mode and elapsed_jam > self.t_ket_limit:
                # BẮT ĐẦU CỨU TRẠM B (20s)
                self.in_relief_mode = True
                self.last_relief_time = curr_time
                cmd = "m2" # Gửi m2 (20s) để xả hướng ngược lại/hướng B
                print(f"[LOGIC] Kẹt quá 150s -> Xả cứu trạm B trong 20s (m2)")
            
            elif self.in_relief_mode:
                # Đang trong 20s cứu trạm B
                if curr_time - self.last_relief_time < self.t_relief:
                    cmd = "m2"
                    print(f"[LOGIC] Đang cứu trạm B... {int(self.t_relief - (curr_time - self.last_relief_time))}s")
                else:
                    # Hết 20s cứu, quay lại xả trạm A tiếp
                    self.in_relief_mode = False
                    self.jam_start_time = curr_time # Reset mốc 150s mới
                    cmd = "A"
                    print(f"[LOGIC] Hết 20s cứu B -> Quay lại xả kẹt trạm A (Lệnh A)")
            else:
                # Đang xả kẹt trạm A bình thường
                cmd = "A"
                print(f"[LOGIC] Đang xả kẹt trạm A (CNN: Ket Xe) | Đã kẹt: {int(elapsed_jam)}s")

            # Trong lúc kẹt: KHÔNG CHẠY YOLO, GỬI LỆNH VÀ THOÁT
            self.uart.send(cmd)
            self.eth.send_data(True, 0)
            return self._build_result(status_local, 0, brightness, input_image_url), cmd

        # 4. LOGIC KHI HẾT KẸT (CNN báo "Binh Thuong" - biến a)
        else:
            if self.is_jamming:
                print(f"[LOGIC] CNN báo HẾT KẸT! Chờ 5s để ổn định hệ thống...")
                time.sleep(5) # Trễ 5s như bạn yêu cầu trước khi đổi sang YOLO
                self.is_jamming = False
                self.in_relief_mode = False

            # CHẠY YOLO ĐỂ ĐIỀU KHIỂN THEO LƯỢNG XE
            yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)
            self.eth.send_data(False, xe_local)
            
            remote_data = self.eth.get_remote_status()
            xe_remote = remote_data.get('xe', 0)
            
            # Tính toán mode dựa trên xe_max (khi cả 2 trạm đều "a" - thoáng)
            xe_max = max(xe_local, xe_remote)
            t_m, cmd = self._esp32_mode(xe_max)
            
            print(f"[LOGIC] Trạng thái THOÁNG -> YOLO đếm xe: {xe_local} | Lệnh: {cmd}")
            self.uart.send(cmd)
            return self._build_result(status_local, xe_local, brightness, input_image_url), cmd

    def _esp32_mode(self, total):
        if total < 5: return self.t_modes['m1'], "m1"
        elif total <= 10: return self.t_modes['m2'], "m2"
        elif total <= 20: return self.t_modes['m3'], "m3"
        return self.t_modes['m4'], "m4"

    def _build_result(self, status, xe, bright, url):
        return {
            "cnn_status": status,
            "xe_local": xe,
            "brightness": round(bright, 2),
            "input_image": url
        }

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"