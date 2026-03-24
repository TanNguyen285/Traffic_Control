import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import cv2
import base64
import os
import json

class TrafficEngine:
    def __init__(self, yolo_ai, cnn_model, cnn_transform, cnn_classes, device, pre_proc, uart, cam):
        self.ai = yolo_ai
        self.cnn_net = cnn_model
        self.cnn_transform = cnn_transform
        self.cnn_classes = cnn_classes
        self.device = device
        self.pre_proc = pre_proc
        self.uart = uart
        self.cam = cam

    def predict_cnn(self, cv2_frame):
        if self.cnn_net is None: return "N/A", 0.0
        rgb_img = cv2.cvtColor(cv2_frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        input_tensor = self.cnn_transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.cnn_net(input_tensor)
            probs = F.softmax(outputs, dim=1)[0]
            idx = torch.argmax(probs).item()
            conf = probs[idx].item() * 100
        return self.cnn_classes[idx], conf

    def calculate_signal(self, total):
        if total < 5: return 20, "m1"
        elif total <= 10: return 45, "m2"
        elif total <= 20: return 60, "m3"
        return 90, "m4"

    def perform_detection(self, selected_image=None):
        # 1. Lấy ảnh
        frame = selected_image if selected_image is not None else self.cam.read()[1]
        if frame is None: return {"error": "Không có dữ liệu ảnh"}, "m0"

        # 2. Chạy CNN Phân loại
        status, conf = self.predict_cnn(frame)

        # 3. Chạy YOLO Đếm xe
        ready_frame, brightness = self.pre_proc.process(frame, roi_box=[0.1, 0.9, 0.0, 1.0])
        result, total = self.ai.detect(ready_frame, brightness)

        # 4. Tính toán kết quả
        total_sec, cmd = self.calculate_signal(total)
        
        result.update({
            "cnn_status": status,
            "cnn_confidence": f"{conf:.2f}%",
            "total_seconds": total_sec,
            "green_seconds": max(0, total_sec - 3)
        })

        # Encode ảnh base64 để hiển thị web
        _, buf = cv2.imencode('.jpg', frame)
        result['input_image'] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

        # 5. Gửi UART
        self.uart.send(cmd)
        
        return result, cmd