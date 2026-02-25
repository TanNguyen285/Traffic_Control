import cv2
import os
import uuid
import time
import json

class Yolo_AI:
    def __init__(self, model_obj, class_names):
        self.model = model_obj
        self.class_names = class_names

    def detect(self, processed_frame, output_dir, static_dir, brightness_val):
        """
        processed_frame: Ảnh 640x640 đã qua xử lý Gamma/CLAHE/ROI
        """
        try:
            # 1. Chạy YOLO
            results = self.model(processed_frame, conf=0.5)
            img_out = results[0].plot()
            
            # 2. Lưu ảnh kết quả
            timestamp = str(uuid.uuid4())[:8]
            det_filename = f"det_{timestamp}.jpg"
            output_path = os.path.join(output_dir, det_filename)
            cv2.imwrite(output_path, img_out)

            # 3. Đếm xe
            num_classes = len(self.class_names)
            counts = [0] * num_classes
            
            boxes = results[0].boxes
            if hasattr(boxes, 'cls'):
                for c in boxes.cls:
                    idx = int(c)
                    if 0 <= idx < num_classes:
                        counts[idx] += 1
            
            total = sum(counts)
            
            # 4. Logic tính giây và lệnh UART
            if total < 5: sec, cmd = 20, "m1"
            elif total <= 10: sec, cmd = 45, "m2"
            elif total <= 20: sec, cmd = 60, "m3"
            else: sec, cmd = 90, "m4"

            # 5. Đóng gói kết quả
            res = {
                "processed_image_url": f"/static/outputs/{det_filename}",
                "input_image_url": f"/static/uploads/raw_last.jpg",
                "counts": counts,
                "total_vehicles": total,
                "total_seconds": sec,
                "brightness": round(brightness_val, 2), # Thêm thông số ánh sáng
                "timestamp": int(time.time())
            }

            # 6. Ghi log JSON
            log_path = os.path.join(static_dir, 'last_detection.json')
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(res, f, ensure_ascii=False)

            return res, cmd

        except Exception as e:
            print(f"--- Lỗi VisionAI: {e} ---")
            return {"error": str(e)}, "m0"