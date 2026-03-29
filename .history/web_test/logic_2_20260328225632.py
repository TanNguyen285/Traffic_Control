import cv2
import base64
import time
import sys

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
        self.t_cho = 0 

        self.t_modes = {
            'm1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'A': t_ket
        }
        self.t_y = t_y
        self.time_g = t_m1 
        
        # Thêm biến để đếm thời gian thực cho việc xả cứu trạm B
        self.last_time_check = time.time()

    def AI_CNN_SCI(self, selected_image=None):
        # 1. Lấy ảnh và Tiền xử lý
        is_upload = selected_image is not None
        frame_raw = selected_image if is_upload else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        input_image_url = self._to_base64_url(frame_raw)
        frame_cnn, frame_yolo, brightness = self.pre_proc.input_yolo_cnn(frame_raw, skip_roi=is_upload)

        # 2. Nhận diện CNN liên tục
        status_local, conf_local, _ = self.cnn.predict(frame_cnn)
        is_jam_local = (status_local == "Ket Xe")
        
        # --- LOGIC QUAN TRỌNG: NẾU KẸT THÌ KHÔNG CHẠY YOLO ---
        if is_jam_local:
            xe_local = 0 # Không chạy YOLO để tiết kiệm tài nguyên
        else:
            yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)

        # --- Giao tiếp qua Ethernet ---
        self.eth.send_data(is_jam_local, xe_local)
        remote_data = self.eth.get_remote_status()

        # 3. Gán biến A/a, B/b dựa trên ID trạm (GIỮ NGUYÊN)
        if self.id == 'A':
            A, a = is_jam_local, not is_jam_local
            B = remote_data.get('ket', False)
            b = not B
            xe_a, xe_b = xe_local, remote_data.get('xe', 0)
        else:
            B, b = is_jam_local, not is_jam_local
            A = remote_data.get('ket', False)
            a = not A
            xe_b, xe_a = xe_local, remote_data.get('xe', 0)

        cmd = "m1"
        t_m = self.t_modes['m1']

        # 4. LOGIC PHÂN XỬ + CẬP NHẬT T_CHO THỜI GIAN THỰC
        now = time.time()
        dt = now - self.last_time_check
        self.last_time_check = now

        if A and (B or b):
            if self.t_cho > 150:
                t_m, cmd, self.t_cho = 20, "m2", 0
                print(f"\n[XẢ CỨU] Đã kẹt quá 150s, xả trạm B 20s...")
            else:
                t_m, cmd = self.t_modes['A'], "A"
                self.t_cho += dt # Cộng dồn thời gian kẹt thực tế
                sys.stdout.write(f"\r[KẸT XE] Đang xả trạm A: {int(self.t_cho)}s/150s | CNN: {status_local}  ")
                sys.stdout.flush()

        elif B and a:
            if self.t_cho > 150:
                t_m, cmd, self.t_cho = 20, "m2", 0
            else:
                t_m, cmd = self.t_modes['A'], "A"
                self.t_cho += dt
                sys.stdout.write(f"\r[KẸT XE] Remote kẹt, đang xả A: {int(self.t_cho)}s/150s  ")
                sys.stdout.flush()

        elif a and b:
            # Nếu cả 2 đều thoáng (a và b)
            if self.is_jam_local_old: # Vừa thoát kẹt xong
                 time.sleep(5) # Đợi 5s ổn định như bạn muốn
            
            self.t_cho = 0
            xe_max = max(xe_a, xe_b)
            t_m, cmd = self._esp32_mode(xe_max)
            sys.stdout.write(f"\r[THOÁNG] YOLO chạy: {xe_local} xe | Lệnh: {cmd}  ")
            sys.stdout.flush()
        
        self.is_jam_local_old = is_jam_local # Lưu trạng thái để check thoát kẹt

        # 5. Cập nhật và Trả về (GIỮ NGUYÊN)
        self.green_duration = t_m
        result = {
            "cnn_status": status_local,
            "xe_local": xe_local,
            "xe_remote": xe_b if self.id == 'A' else xe_a,
            "remote_jam": B if self.id == 'A' else A,
            "brightness": round(brightness, 2),
            "input_image": input_image_url
        }

        self.uart.send(cmd)
        return result, cmd

    def _esp32_mode(self, total):
        if total < 5: return self.t_modes['m1'], "m1"
        elif total <= 10: return self.t_modes['m2'], "m2"
        elif total <= 20: return self.t_modes['m3'], "m3"
        return self.t_modes['m4'], "m4"

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"