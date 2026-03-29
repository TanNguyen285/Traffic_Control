import cv2
import base64
import time

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam):
        self.ai = yolo_ai            # Service YOLO đã tách riêng
        self.cnn = cnn_service      # Service CNN mới tách
        self.pre_proc = pre_proc    # Module SCI tiền xử lý
        self.uart = uart
        self.cam = cam

    def perform_detection(self, selected_image=None):
        # 1. Kiểm tra nguồn ảnh
        is_upload = selected_image is not None
        frame_raw = selected_image if is_upload else self.cam.read()[1]
        
        if frame_raw is None: 
            return {"error": "No Frame"}, "m0"

        # Encode ảnh gốc cho Frontend
        input_image_url = self._to_base64_url(frame_raw)

        # 2. Tiền xử lý SCI
        # Nếu là ảnh upload (is_upload=True), ta có thể truyền thêm cờ hoặc xử lý riêng
        # Nhưng theo yêu cầu của bạn, ta sẽ sửa process_dual để xử lý logic này
        frame_cnn, frame_yolo, brightness = self.pre_proc.process_dual(frame_raw, skip_roi=is_upload)

        # 3. Sử dụng CNN Service để kiểm tra trạng thái
        status, conf, _ = self.cnn.predict(frame_cnn)
        
        result = {
            "cnn_status": status,
            "cnn_confidence": f"{conf:.2f}%",
            "brightness": round(brightness, 2),
            "timestamp": int(time.time()),
            "input_image": input_image_url
        }

        # 4. Quyết định luồng xử lý
        if status == "Ket Xe":
            total_sec, cmd = 90, "m4"
            result.update({
                "total_vehicles": "Kẹt xe", 
                "counts": [0,0,0,0,0],
                "processed_image": self._draw_jam_alert(frame_yolo)
            })
        else:
            yolo_res, total = self.ai.detect(frame_yolo, brightness)
            total_sec, cmd = self._calculate_signal(total)
            result.update(yolo_res)

        # 5. Đóng gói kết quả & UART
        result.update({
            "total_seconds": total_sec,
            "green_seconds": max(0, total_sec - 3)
        })
        
        self.uart.send(cmd)
        return result, cmd

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        b64 = base64.b64encode(buf).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"

    def _draw_jam_alert(self, frame):
        """ Vẽ thông báo kẹt xe trực tiếp lên ảnh """
        canvas = frame.copy()
        cv2.rectangle(canvas, (0, 0), (640, 70), (0, 0, 0), -1)
        cv2.putText(canvas, "TRANG THAI: KET XE", (20, 45), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        return self._to_base64_url(canvas)

    def _c(self, total):
        """ Logic tính toán thời gian đèn """
        if total < 5: return 20, "m1"
        elif total <= 10: return 45, "m2"
        elif total <= 20: return 60, "m3"
        return 90, "m4"