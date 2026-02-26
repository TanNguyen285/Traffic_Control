import cv2
import os
import uuid
import time
import json


class Yolo_AI:
    def __init__(self, model_obj, class_names):
        self.model = model_obj
        self.class_names = class_names

    def detect(self, processed_frame, brightness_val):
        """
        processed_frame: Ảnh 640x640 đã qua xử lý (ROI / SCI / Gamma...)
        brightness_val: giá trị độ sáng đã tính trước đó
        """

        try:
            # ================= 1️⃣ Chạy YOLO =================
            results = self.model(processed_frame, conf=0.5)

            if not results or len(results) == 0:
                return {"error": "No detection results"}, 0

            img_out = results[0].plot()

            # ================= 2️⃣ Đếm số lượng theo class =================
            num_classes = len(self.class_names)
            counts = [0] * num_classes

            boxes = results[0].boxes

            if boxes is not None and hasattr(boxes, 'cls'):
                try:
                    cls_list = [int(x) for x in boxes.cls]
                except Exception:
                    cls_list = []

                for idx in cls_list:
                    if 0 <= idx < num_classes:
                        counts[idx] += 1

            total = sum(counts)

            # ================= 3️⃣ Đóng gói kết quả (base64 image)
            res = {
                "counts": counts,
                "total_vehicles": total,
                "brightness": round(brightness_val, 2),
                "timestamp": int(time.time())
            }

            try:
                import base64
                _, buf = cv2.imencode('.jpg', img_out)
                b64 = base64.b64encode(buf).decode('utf-8')
                res['processed_image'] = f"data:image/jpeg;base64,{b64}"
            except Exception:
                pass

            return res, total

        except Exception as e:
            print(f"--- Lỗi Yolo_AI.detect(): {e} ---")
            return {"error": str(e)}, 0