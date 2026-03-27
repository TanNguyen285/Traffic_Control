import cv2
import os
import uuid
import time
import json
import base64 # Cần dùng để chuyển ảnh sang dạng chuỗi gửi lên Web

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
        - processed_frame: Ảnh 640x640 đã được tiền xử lý (ROI, Gamma, SCI...)
        - brightness_val: Giá trị độ sáng đã được tính toán từ trước
        """

        try:
            # ================= 1️⃣ CHẠY DỰ ĐOÁN YOLO =================
            # conf=0.3: Chỉ lấy các đối tượng có độ tự tin trên 30%
            results = self.model.predict(processed_frame, conf=0.3)
            
            # Kiểm tra nếu không có kết quả trả về
            if not results or len(results) == 0:
                return {"error": "No detection results"}, 0

            # Vẽ các khung bao (bounding boxes) và nhãn lên ảnh để hiển thị
            img_out = results[0].plot()

            # ================= 2️⃣ THỐNG KÊ SỐ LƯỢNG THEO LỚP =================
            num_classes = len(self.class_names)
            # Khởi tạo danh sách đếm toàn số 0 (ví dụ: [0, 0, 0, 0, 0])
            counts = [0] * num_classes

            # Lấy danh sách các hộp nhận diện được
            boxes = results[0].boxes

            if boxes is not None and hasattr(boxes, 'cls'):
                try:
                    # Lấy danh sách ID của các class (ví dụ: [0, 0, 2, 1])
                    cls_list = [int(x) for x in boxes.cls]
                except Exception:
                    cls_list = []

                # Duyệt qua từng ID và tăng biến đếm tương ứng
                for idx in cls_list:
                    if 0 <= idx < num_classes:
                        counts[idx] += 1

            # Tổng số lượng phương tiện nhận diện được
            total = sum(counts)

            # ================= 3️⃣ ĐÓNG GÓI DỮ LIỆU KẾT QUẢ =================
            res = {
                "counts": counts,             # Mảng số lượng từng loại xe
                "total_vehicles": total,      # Tổng số xe
                "brightness": round(brightness_val, 2), # Độ sáng ảnh
                "timestamp": int(time.time()) # Thời gian thực hiện
            }

            # Chuyển đổi ảnh đã vẽ khung (img_out) sang định dạng Base64 
            # để hiển thị trực tiếp lên trình duyệt (thẻ <img>)
            try:
                # Mã hóa ảnh sang định dạng JPG
                _, buf = cv2.imencode('.jpg', img_out)
                # Chuyển mảng byte sang chuỗi Base64
                b64 = base64.b64encode(buf).decode('utf-8')
                # Thêm tiền tố để trình duyệt hiểu đây là dữ liệu ảnh
                res['processed_image'] = f"data:image/jpeg;base64,{b64}"
            except Exception:
                pass

            # Trả về từ điển kết quả và tổng số xe để logic bên ngoài xử lý tiếp
            return res, total

        except Exception as e:
            print(f"--- Lỗi Yolo_AI.detect(): {e} ---")
            return {"error": str(e)}, 0