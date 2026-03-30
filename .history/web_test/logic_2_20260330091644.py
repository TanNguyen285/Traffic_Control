import cv2
import base64
import sys
from timer import Timer

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, eth_service, station_id='A',
                 t_m1=15, t_m2=20, t_m3=25, t_m4=40, t_ket=150):
        
        self.ai = yolo_ai            
        self.cnn = cnn_service      
        self.pre_proc = pre_proc    
        self.uart = uart
        self.cam = cam
        self.eth = eth_service 
        
        self.id = station_id.upper()
        self.jam_timer = Timer(f"jam_{self.id}") 
        self.relief_timer = Timer(f"relief_{self.id}")

        self.t_modes = {
            'm1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'A': t_ket
        }
        self.is_jam_local_old = False

    def AI_CNN_SCI(self, selected_image=None):
        # 1. Lấy ảnh và Tiền xử lý
        is_upload = selected_image is not None
        frame_raw = selected_image if is_upload else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        frame_cnn, frame_yolo, brightness = self.pre_proc.input_yolo_cnn(frame_raw, skip_roi=is_upload)

        # 2. Nhận diện CNN để xác định kẹt (Local)
        status_local, _, _ = self.cnn.predict(frame_cnn)
        ket_local = (status_local == "Ket Xe")
        
        # --- LOGIC QUYẾT ĐỊNH MODE DỰA TRÊN YOLO ---
        xe_local = 0
        if ket_local:
            mode_local = "m"  # Ký hiệu đang kẹt
            yolo_res = {"yolo_image": self._to_base64_url(frame_yolo)}
        else:
            yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)
            # Tự tính toán mode dựa trên số xe đếm được tại trạm này
            _, mode_local = self._esp32_mode(xe_local) 

        # --- Giao tiếp qua Ethernet: Gửi trạng thái kẹt và MODE (m1-m4) ---
        self.eth.send_data(ket_local, mode_local)
        remote_data = self.eth.get_remote_status()

        # 3. Phân tích dữ liệu từ trạm xa (Remote)
        ket_remote = remote_data.get('ket', False)
        mode_remote = remote_data.get('mode', 'm1') # Nhận về m1, m2, m3, hoặc m4

        # Biến điều khiển cuối cùng
        cmd = "m1"
        t_m = self.t_modes['m1']

        # 4. LOGIC PHÂN XỬ
        # TRƯỜNG HỢP 1: TRẠM NÀY ĐANG KẸT
        if ket_local:
            self.jam_timer.start()
            if self.jam_timer.get_elapsed() > 150:
                self.relief_timer.start()
                if self.relief_timer.get_elapsed() < 20:
                    t_m, cmd = 20, "m2" # Ưu tiên xả cứu trạm đối diện
                else:
                    self.jam_timer.reset()
                    self.relief_timer.reset()
                    t_m, cmd = self.t_modes['A'], "A"
            else:
                t_m, cmd = self.t_modes['A'], "A"

        # TRƯỜNG HỢP 2: TRẠM KIA KẸT, TRẠM NÀY THOÁNG
        elif ket_remote and not ket_local:
            self.jam_timer.start()
            if self.jam_timer.get_elapsed() > 150:
                t_m, cmd = 20, "m2"
                self.jam_timer.reset()
            else:
                t_m, cmd = self.t_modes['A'], "A"

        # TRƯỜNG HỢP 3: CẢ HAI CÙNG THOÁNG (Dùng MODE cao nhất giữa 2 trạm)
        else:
            self.jam_timer.reset()
            self.relief_timer.reset()
            
            # So sánh cấp độ mode: ví dụ m4 > m1
            # Ép kiểu lấy ký tự số ở cuối (ví dụ 'm3' -> 3) để so sánh
            try:
                val_local = int(mode_local[1]) if len(mode_local) > 1 else 1
                val_remote = int(mode_remote[1]) if len(mode_remote) > 1 else 1
                
                final_mode_val = max(val_local, val_remote)
                cmd = f"m{final_mode_val}"
            except:
                cmd = "m1"
                
            t_m = self.t_modes.get(cmd, self.t_modes['m1'])
            sys.stdout.write(f"\r[THOÁNG] Local: {mode_local} | Remote: {mode_remote} -> Chọn: {cmd} ({t_m}s)")
            sys.stdout.flush()

        # 5. Gửi lệnh xuống ESP32 và cập nhật kết quả
        self.uart.send(cmd)
        self.is_jam_local_old = ket_local

        result = {
            "cnn_status": status_local,
            "mode_local": mode_local,
            "mode_remote": mode_remote,
            "remote_jam": ket_remote,
            "brightness": round(brightness, 2),
            "counts": yolo_res.get("counts", [0, 0, 0, 0, 0]),
            "input_image": self._to_base64_url(frame_raw), 
            "yolo_image": yolo_res.get('yolo_image')
        }
        return result, cmd

    def _esp32_mode(self, total):
        if total < 5: return self.t_modes['m1'], "m1"
        elif total <= 10: return self.t_modes['m2'], "m2"
        elif total <= 20: return self.t_modes['m3'], "m3"
        return self.t_modes['m4'], "m4"

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"