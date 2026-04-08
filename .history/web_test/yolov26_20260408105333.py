import cv2
import os
import uuid
import time
import json
import base64 

class Yolo_AI:
    def __init__(self, model_obj, class_names):
        """
        Khởi tạo bộ nhận diện YOLO.
        - model_obj: Đối tượng model đã load (yolo_model)
        - class_names: Danh sách tên các loại xe (car, bus, motorcycle...)
        """
        self.model = model_obj
        self.class_names = class_names

    def detect(self, processed_frame, brightness_val):
        """
        Thực hiện nhận diện và thống kê.
        """
        try:
            # ================= 1️⃣ CHẠY DỰ ĐOÁN YOLO =================
            results = self.model.predict(processed_frame, conf=0.4)
            
            if not results or len(results) == 0:
                # Trả về cấu trúc mặc định để tránh lỗi ở TrafficLogic
                return {"counts": [0]*len(self.class_names), "xe_local": 0, "yolo_image": None}, 0

            # Vẽ các khung bao (bounding boxes)
            img_out = results[0].plot()

            # ================= 2️⃣ THỐNG KÊ SỐ LƯỢNG THEO LỚP =================
            num_classes = len(self.class_names)
            counts = [0] * num_classes

            boxes = results[0].boxes
            if boxes is not None and hasattr(boxes, 'cls'):
                try:
                    cls_list = [int(x) for x in boxes.cls]
                    for idx in cls_list:
                        if 0 <= idx < num_classes:
                            counts[idx] += 1
                except Exception:
                    pass

            # Tổng số lượng phương tiện
            total = sum(counts)

            # ================= 3️⃣ ĐÓNG GÓI DỮ LIỆU KẾT QUẢ =================
            # Sửa key "total_vehicles" thành "xe_local" để khớp với TrafficLogic và Frontend
            res = {
                "counts": counts,             
                "xe_local": total,            # Đã sửa ở đây
                "brightness": round(brightness_val, 2),
                "timestamp": int(time.time())
            }

            # Chuyển đổi ảnh sang Base64
            try:
                _, buf = cv2.imencode('.jpg', img_out)
                b64 = base64.b64encode(buf).decode('utf-8')
                res['yolo_image'] = f"data:image/jpeg;base64,{b64}"
            except Exception:
                res['yolo_image'] = None

            # Trả về res (dictionary) và total (int) cho TrafficLogic
            return res, total

        except Exception as e:
            print(f"--- Lỗi Yolo_AI.detect(): {e} ---")
            # Trả về giá trị an toàn khi có lỗi
            return {"error": str(e), "counts": [0]*len(self.class_names), "xe_local": 0}, 0