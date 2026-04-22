import cv2
import os
import json

class Yolo_AI:
    def __init__(self, model_obj, class_names):
        self.model = model_obj
        self.class_names = class_names

    def detect(self, processed_frame, brightness_val):
        """
        Thực hiện nhận diện và thống kê.
        - Trả về: dict kết quả (không chứa base64) và tổng số xe.
        """
        try:
            # 1️⃣ CHẠY DỰ ĐOÁN YOLO
            results = self.model.predict(processed_frame, conf=0.4)
            
            if not results or len(results) == 0:
                return {"counts": [0]*len(self.class_names), "xe_local": 0, "frame": None}, 0

            # Vẽ khung bao (Vẫn vẽ để hiển thị lên web)
            img_out = results[0].plot()

            # 2️⃣ THỐNG KÊ SỐ LƯỢNG THEO LỚP
            num_classes = len(self.class_names)
            counts = [0] * num_classes

            boxes = results[0].boxes
            if boxes is not None and hasattr(boxes, 'cls'):
                cls_list = [int(x) for x in boxes.cls]
                for idx in cls_list:
                    if 0 <= idx < num_classes:
                        counts[idx] += 1

            total = sum(counts)

            # 3️⃣ ĐÓNG GÓI DỮ LIỆU (CHỈ GỬI FRAME DẠNG MẢNG)
            res = {
                "counts": counts,             
                "xe_local": total,
                "brightness": round(brightness_val, 2),
                "frame": img_out  # <--- Trả về ảnh gốc để TrafficLogic ghi file .jpg
            }

            return res, total

        except Exception as e:
            print(f"--- Lỗi Yolo_AI.detect(): {e} ---")
            return {"counts": [0]*len(self.class_names), "xe_local": 0, "frame": None}, 0