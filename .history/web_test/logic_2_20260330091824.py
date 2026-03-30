import cv2
import base64
import sys
from timer import Timer


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
        self.jam_timer = Timer("jam_A") # Sẽ tạo file timer_jam_A.json
        # SỬ DỤNG FILE TIME.PY CỦA BẠN
        self.jam_timer = Timer("jam_A")    # Đếm 150s kẹt
        self.relief_timer = Timer("relief_A") # Đếm 20s cứu B

        self.t_modes = {
            'm1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'A': t_ket
        }
        self.t_y = t_y
        self.is_jam_local_old = False

    def AI_CNN_SCI(self, selected_image=None):
        # 1. Lấy ảnh và Tiền xử lý
        is_upload = selected_image is not None
        frame_raw = selected_image if is_upload else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        input_image_url = self._to_base64_url(frame_raw)
        frame_cnn, frame_yolo, brightness = self.pre_proc.input_yolo_cnn(frame_raw, skip_roi=is_upload)

        # 2. Nhận diện CNN liên tục
        status_local, conf_local, _ = self.cnn.predict(frame_cnn)
        ket_local = (status_local == "Ket Xe")
        
        # --- LOGIC: KẸT THÌ NGHỈ YOLO ---
        if ket_local:
            xe_local = 0 
            yolo_res = {"yolo_image": self._to_base64_url(frame_yolo)}
        else:
            yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)
            counts_local = yolo_res.get("counts", [0, 0, 0, 0, 0])

        # --- Giao tiếp qua Ethernet ---
        self.eth.send_data(ket_local, xe_local)
        remote_data = self.eth.get_remote_status()

        # 3. Gán biến A/a, B/b dựa trên ID trạm
        if self.id == 'A':
            A, a = ket_local, not ket_local
            B = remote_data.get('ket', False)
            b = not B
            xe_a, xe_b = xe_local, remote_data.get('xe', 0)
        else:
            B, b = ket_local, not ket_local
            A = remote_data.get('ket', False)
            a = not A
            xe_b, xe_a = xe_local, remote_data.get('xe', 0)

        cmd = "m1"
        t_m = self.t_modes['m1']

        # 4. LOGIC PHÂN XỬ DÙNG TRAFFICTIMER CỦA BẠN
        if A and (B or b):
            self.jam_timer.start() # Bắt đầu đếm kẹt
            
            # Kiểm tra nếu đã kẹt quá 150s
            if self.jam_timer.get_elapsed() > 150:
                self.relief_timer.start() # Bắt đầu đếm 20s cứu B
                
                if self.relief_timer.get_elapsed() < 20:
                    t_m, cmd = 20, "m2"
                    self.relief_timer.show_debug("XẢ CỨU TRẠM B", 20)
                else:
                    # Hết 20s cứu -> Reset cả 2 để quay lại xả A
                    self.jam_timer.reset()
                    self.relief_timer.reset()
                    t_m, cmd = self.t_modes['A'], "A"
            else:
                t_m, cmd = self.t_modes['A'], "A"
                self.jam_timer.show_debug(f"XẢ KẸT TRẠM {self.id}", 150)

        elif B and a:
            # Tương tự cho trường hợp trạm kia kẹt
            self.jam_timer.start()
            if self.jam_timer.get_elapsed() > 150:
                t_m, cmd = 20, "m2"
                self.jam_timer.reset() # Hoặc xử lý theo ý bạn
            else:
                t_m, cmd = self.t_modes['A'], "A"
                self.jam_timer.show_debug("REMOTE KẸT - ĐANG XẢ", 150)

        elif a and b:
            # --- TRẠNG THÁI THOÁNG (Cả 2 trạm cùng xác nhận thoáng) ---
            
            # 1. Reset các bộ đếm kẹt vì đã thông xe
            self.jam_timer.reset()
            self.relief_timer.reset()

            # 2. CHẠY YOLO NGAY LẬP TỨC để quyết định mode
            yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)
            
            # Lấy dữ liệu xe từ trạm B qua Ethernet
            xe_remote = remote_data.get('xe', 0)
            xe_max = max(xe_local, xe_remote)
            
            # Xác định mode m1->m4 dựa trên số xe lớn nhất
            t_m, cmd = self._esp32_mode(xe_max)

            # 3. GỬI LỆNH XẢ THEO YOLO XUỐNG ESP32
            # ESP32 nhận được m1-m4 sẽ tự hiểu là đã thoát kẹt và chạy theo time YOLO
            self.uart.send(cmd)
            
            # 4. ĐỒNG BỘ VỚI TRẠM B VÀ HIỂN THỊ DEBUG
            self.eth.send_data(False, xe_local) # Gửi biến 'a' (False) và số xe cho trạm B

            sys.stdout.write(f"\r[THOÁNG] CNN: OK | YOLO: {xe_local} xe | Gửi ESP32: {cmd} ({t_m}s)    ")
            sys.stdout.flush()

        # Lưu trạng thái để vòng lặp sau đối chiếu
        self.is_jam_local_old = ket_local

        # 5. Cập nhật và Trả về
        self.green_duration = t_m
        result = {
    "cnn_status": status_local,# trạng thái kẹt xe của trạm này
    "xe_local": xe_local,
    "xe_remote": xe_b if self.id == 'A' else xe_a,#trạng thái kẹt xe gửi đi
    "remote_jam": B if self.id == 'A' else A,#trạng thái kẹt của trạm B
    "brightness": round(brightness, 2),
    "counts": yolo_res.get("counts", [0, 0, 0, 0, 0]),#class
    "input_image": self._to_base64_url(frame_raw), 
    "yolo_image": yolo_res.get('yolo_image')#ảnh YOLO (đã vẽ khung) để hiển thị trên web
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