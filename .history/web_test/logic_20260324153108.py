import torch
import torch.nn.functional as F
from PIL import Image
import cv2
import base64

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
        """ Dự đoán trực tiếp trên frame đã resize 224 """
        if self.cnn_net is None: return "N/A", 0.0
        
        # Chuyển từ BGR (OpenCV) sang RGB và Tensor
        rgb = cv2.cvtColor(frame_cnn_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        
        # Lưu ý: cnn_transform của bạn không cần Resize nữa vì pre_proc đã làm rồi
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
        # 1. Lấy ảnh gốc
        frame_raw = selected_image if selected_image is not None else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        # 2. Tiền xử lý tập trung (Chạy SCI 1 lần, tách 2 nhánh)
        # roi_box=[y1, y2, x1, x2]
        frame_cnn, frame_yolo, brightness = self.pre_proc.process_dual(frame_raw, roi_box=[0.1, 0.9, 0.0, 1.0])

        # 3. Chạy CNN trên frame_cnn (224x224)
        status, conf = self.predict_cnn(frame_cnn)

        result = {
            "cnn_status": status,
            "cnn_confidence": f"{conf:.2f}%",
            "brightness": f"{brightness:.2f}"
        }

        # 4. Nhánh quyết định
        if status == "Ket Xe":
            total_sec, cmd = 90, "m4"
            result.update({"total_vehicles": "N/A (Kẹt xe)", "counts": {}})
        else:
            # Chỉ chạy YOLO trên frame_yolo (640x640) nếu KHÔNG kẹt xe
            yolo_res, total = self.ai.detect(frame_yolo, brightness)
            total_sec, cmd = self.calculate_signal(total)
            result.update(yolo_res)

        # 5. Kết quả & UART
        result.update({"total_seconds": total_sec, "green_seconds": max(0, total_sec - 3)})
        
        # Encode ảnh gốc hoặc ảnh đã qua SCI để xem trên Web
        _, buf = cv2.imencode('.jpg', frame_yolo) # Hiển thị ảnh 640 cho đẹp
        result['input_image'] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"
        
        self.uart.send(cmd)
        return result, cmd