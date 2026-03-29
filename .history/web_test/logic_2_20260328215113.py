import cv2
import base64
import time

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, station_id='A',
                 t_m1=15, t_m2=20, t_m3=25, t_m4=40, t_ket=150, t_y=3):
        
        self.ai = yolo_ai            
        self.cnn = cnn_service      
        self.pre_proc = pre_proc    
        self.uart = uart
        self.cam = cam
        
        self.id = station_id.upper()
        self.t_cho = 0  # Biến đếm tích lũy thời gian chờ (giây)

        # Cấu hình thời gian
        self.t_modes = {
            'm1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'A ': t_ket
        }
        self.t_y = t_y
        self.time_g = t_m1 

    def AI_CNN_SCI(self, selected_image=None, remote_data=None):
        """
        remote_data: {'ket': bool, 'xe': int} từ trạm đối diện
        """
        # 1. Lấy ảnh và Tiền xử lý
        is_upload = selected_image is not None
        frame_raw = selected_image if is_upload else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        input_image_url = self._to_base64_url(frame_raw)
        frame_cnn, frame_yolo, brightness = self.pre_proc.input_yolo_cnn(frame_raw, skip_roi=is_upload)

        # 2. Nhận diện trạng thái tại chỗ
        status_local, conf_local, _ = self.cnn.predict(frame_cnn)
        is_jam_local = (status_local == "Ket Xe")
        yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)

        # 3. Gán biến trạng thái theo ký hiệu bạn muốn (A/a, B/b)
        # A, B = Kẹt | a, b = Thoáng
        if self.id == 'A':
            A = is_jam_local          # Trạng thái trạm mình (A)
            a = not is_jam_local
            B = remote_data.get('ket', False) if remote_data else False
            b = not B
            xe_a, xe_b = xe_local, (remote_data.get('xe', 0) if remote_data else 0)
        else:
            B = is_jam_local          # Trạng thái trạm mình (B)
            b = not is_jam_local
            A = remote_data.get('ket', False) if remote_data else False
            a = not A
            xe_b, xe_a = xe_local, (remote_data.get('xe', 0) if remote_data else 0)

        cmd = "m1"
        t_m = self.t_modes['m1']

        # 4. LOGIC PHÂN XỬ THEO YÊU CẦU CỦA BẠN
        
        # --- TRƯỜNG HỢP 1: A kẹt & (B kẹt hoặc b thoáng) -> Ưu tiên xả A ---
        if A and (B or b):
            if self.t_cho > 150:
                # Nếu B đã phải chờ quá 150s, cho B xả 20s để giải tỏa
                t_m = 20
                cmd = "m2" # Hoặc mode nào bạn quy định cho 20s
                self.t_cho = 0 # Reset sau khi cứu hộ
            else:
                # Xả trạm A (Mode kẹt xe m5)
                t_m = self.t_modes['A']
                cmd = "A"
                self.t_cho += (t_m + self.t_y) # Tích lũy thời gian B phải chờ

        # --- TRƯỜNG HỢP 2: B kẹt & a thoáng -> Ưu tiên xả B ---
        elif B and a:
            if self.t_cho > 150:
                # Nếu A đã phải chờ quá 150s, cho A xả 20s
                t_m = 20
                cmd = "m2"
                self.t_cho = 0
            else:
                # Xả trạm B (Trạm mình gửi m5 để báo kẹt)
                t_m = self.t_modes['m5']
                cmd = "A"
                self.t_cho += (t_m + self.t_y) # Tích lũy thời gian A phải chờ

        # --- TRƯỜNG HỢP 3: a thoáng & b thoáng -> Chạy YOLO quyết định ---
        elif a and b:
            self.t_cho = 0 # Reset thời gian chờ vì cả 2 đều thoáng
            xe_max = max(xe_a, xe_b)
            t_m, cmd = self._esp32_mode(xe_max)

        # 5. Cập nhật và Trả về
        self.green_duration = t_m
        result = {
            "cnn_status": status_local,
            "cnn_confidence": f"{conf_local:.2f}%",
            "brightness": round(brightness, 2),
            "timestamp": int(time.time()),
            "input_image": input_image_url
        }

        self.uart.send(cmd)
        return result, cmd

    def _esp32_mode(self, total):
        if total < 5: return self.t_modes['m1'], "m1"
        elif total <= 10: return self.t_modes['m2'], "m2"
        elif total <= 20: return self.t_modes['m3'], "m3"
        return self.t_modes['m4'], "m4" # Mode cao nhất khi thoáng là m4

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"