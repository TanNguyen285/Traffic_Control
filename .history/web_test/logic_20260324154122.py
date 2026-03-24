import torch
import torch.nn.functional as F
from PIL import Image
import cv2
import base64
import time

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_model, cnn_transform, cnn_classes, device, pre_proc, uart, cam):
        self.ai = yolo_ai
        self.cnn_net = cnn_model
        self.cnn_transform = cnn_transform
        self.cnn_classes = cnn_classes
        self.device = device
        self.pre_proc = pre_proc
        self.uart = uart
        self.cam = cam

    def predict_cnn(self, frame_cnn_cv2):
        """ Dự đoán trạng thái bằng CNN (224x224) """
        if self.cnn_net is None: return "N/A", 0.0, 0
        
        rgb = cv2.cvtColor(frame_cnn_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        input_tensor = self.cnn_transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.cnn_net(input_tensor)
            probs = F.softmax(outputs, dim=1)[0]
            idx = torch.argmax(probs).item()
            conf = probs[idx].item() * 100
        return self.cnn_classes[idx], conf, idx

    def perform_detection(self, selected_image=None):
        # 1. Lấy ảnh đầu vào
        frame_raw = selected_image if selected_image is not None else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        # 2. Tiền xử lý tập trung qua SCI (1 lần duy nhất)
        # Nhánh 1: frame_cnn (224x224), Nhánh 2: frame_yolo (640x640)
        frame_cnn, frame_yolo, brightness = self.pre_proc.process_dual(frame_raw, roi_box=[0.1, 0.9, 0.0, 1.0])

        # 3. CNN kiểm tra trước
        status, conf, status_idx = self.predict_cnn(frame_cnn)
        
        result = {
            "cnn_status": status,
            "cnn_confidence": f"{conf:.2f}%",
            "brightness": round(brightness, 2),
            "timestamp": int(time.time())
        }

        # 4. CHIA NHÁNH LOGIC
        if status == "Ket Xe":
            # --- TRƯỜNG HỢP KẸT XE ---
            total_sec, cmd = 90, "m4"
            result.update({"total_vehicles": "Kẹt xe", "counts": [0,0,0,0,0]})
            
            # Vẽ thông báo KẸT XE lên ảnh 640 để trả về Web
            # Vẽ nền đen che bớt phía trên để chữ nổi bật
            cv2.rectangle(frame_yolo, (0, 0), (640, 70), (0, 0, 0), -1)
            cv2.putText(frame_yolo, "TRANG THAI: KET XE", (20, 45), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3) # Màu Đỏ
            
            # Chuyển ảnh đã vẽ chữ sang base64
            _, buf = cv2.imencode('.jpg', frame_yolo)
            result['processed_image'] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"
        
        else:
            # --- TRƯỜNG HỢP THÔNG THOÁNG ---
            # Chạy YOLO đếm xe (yoloxx.py sẽ tự vẽ box và trả về base64 trong res)
            yolo_res, total = self.ai.detect(frame_yolo, brightness)
            total_sec, cmd = self.calculate_signal(total)
            
            # Gộp kết quả YOLO vào result (bao gồm cả 'processed_image' đã có box xe)
            result.update(yolo_res)

        # 5. Cập nhật thời gian & Gửi tín hiệu
        result.update({
            "total_seconds": total_sec,
            "green_seconds": max(0, total_sec - 3)
        })
        
        self.uart.send(cmd)
        return result, cmd

    def calculate_signal(self, total):
        if total < 5: return 20, "m1"
        elif total <= 10: return 45, "m2"
        elif total <= 20: return 60, "m3"
        return 90, "m4"