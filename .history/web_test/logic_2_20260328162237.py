import cv2
import base64
import time

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, station_id='A',
                 # Cấu hình thời gian Xanh (t_m) cho từng Mode
                 t_m1=15, t_m2=20, t_m3=25, t_m4=40, t_m_ket=60, t_y=3):
        
        self.ai = yolo_ai            
        self.cnn = cnn_service      
        self.pre_proc = pre_proc    
        self.uart = uart
        self.cam = cam
        
        self.id = station_id.upper()
        self.t_cho = 0 # Biến đếm cứu trạm

        # Lưu cấu hình vào dict nội bộ
        self.t_modes = {
            'm1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'm5': t_m_ket
        }
        self.t_y = t_y
        self.time_g = t_m1 

    def perform_detection(self, selected_image=None, remote_data=None):
        """ 
        remote_data: {'ket': bool, 'xe': int}
        """
        # 1. Kiểm tra nguồn ảnh
        is_upload = selected_image is not None# Nếu có ảnh upload, bỏ qua ROI để CNN có thể đánh giá toàn cảnh
        frame_raw = selected_image if is_upload else self.cam.read()[1]#ảnh raw chụp từ camera nếu không có ảnh upload
        
        if frame_raw is None: 
            return {"error": "No Frame"}, "m0"# Trả về lỗi nếu không có ảnh nào được cung cấp (m0=default)

        input_image_url = self._to_base64_url(frame_raw)

        # 2. Tiền xử lý SCI
        frame_cnn, frame_yolo, brightness = self.pre_proc.process_dual(frame_raw, skip_roi=is_upload)

        # 3. Chạy CNN kiểm tra kẹt xe tại chỗ
        status_local, conf_local, _ = self.cnn.predict(frame_cnn)
        ket_local = (status_local == "Ket Xe")
        
        # 4. Chạy YOLO đếm xe
        yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)
        
        # 5. LOGIC SO SÁNH 2 NHÁNH (Phân xử A vs B)
        if self.id == 'A':
            ket_a, xe_a = ket_local, xe_local
            ket_b = remote_data.get('ket') if remote_data else None
            xe_b = remote_data.get('xe') if remote_data else 0
        else:
            ket_b, xe_b = ket_local, xe_local
            ket_a = remote_data.get('ket') if remote_data else None
            xe_a = remote_data.get('xe') if remote_data else 0

        # Mặc định ban đầu
        cmd = "m1"

        # TH1: Mất kết nối trạm kia (Offline)
        if ket_a is None or ket_b is None:
            t_m, cmd = self._calculate_signal(xe_local)
            if ket_local: 
                cmd = "m4"
                t_m = self.t_modes['m_ket']

        # TH2: Ưu tiên xả A (A kẹt)
        elif (ket_a and ket_b) or (ket_a and not ket_b):
            self.t_cho = 0
            cmd = "m4"
            t_m = self.t_modes['m_ket']

        # TH3: Trạm B kẹt
        elif ket_b and not ket_a:
            if self.t_cho > 150: # Ngưỡng cứu hộ A
                self.t_cho = 0
                cmd = "m4"
                t_m = self.t_modes['m4']
            else:
                self.t_cho += 1
                cmd = "m5"
                t_m = self.t_modes['m_ket']

        # TH4: Thông thoáng -> So sánh số xe
        else:
            self.t_cho = 0
            xe_max = max(xe_a, xe_b)
            t_m, cmd = self._esp32_mode(xe_max)

        # Cập nhật thời gian thực (t_r = t_m + t_y)
        self.green_duration = t_m

        # 6. Đóng gói KẾT QUẢ CŨ (Chỉ trả về đúng những gì bạn yêu cầu)
        result = {
            "cnn_status": status_local,
            "cnn_confidence": f"{conf_local:.2f}%",
            "brightness": round(brightness, 2),
            "timestamp": int(time.time()),
            "input_image": input_image_url
        }

        # Thực hiện gửi lệnh qua UART
        self.uart.send(cmd)
        
        return result, cmd

    def _esp32_mode(self, total):
        """ Tính toán t_m và cmd dựa trên cấu hình """
        if total < 5: return self.t_modes['m1'], "m1"
        elif total <= 10: return self.t_modes['m2'], "m2"
        elif total <= 20: return self.t_modes['m3'], "m3"
        return self.t_modes['m5'], "m5"

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"