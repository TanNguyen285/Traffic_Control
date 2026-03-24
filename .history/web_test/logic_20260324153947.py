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
        if self.cnn_net is None: return "N/A", 0.0
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
        frame_raw = selected_image if selected_image is not None else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        # 1. Tiền xử lý (SCI + Resize)
        frame_cnn, frame_yolo, brightness = self.pre_proc.process_dual(frame_raw, roi_box=[0.1, 0.9, 0.0, 1.0])

        # 2. Chạy CNN dự đoán
        status, conf, status_idx = self.predict_cnn(frame_cnn)

        # Chuẩn bị màu sắc: Đỏ cho kẹt xe, Xanh cho thông thoáng
        color = (0, 0, 255) if status_idx == 1 else (0, 255, 0) # BGR
        
        result = {
            "cnn_status": status,
            "cnn_confidence": f"{conf:.2f}%",
            "brightness": f"{brightness:.2f}"
        }

        # 3. Nhánh quyết định và Vẽ lên ảnh
        if status == "Ket Xe":
            total_sec, cmd = 90, "m4"
            result.update({"total_vehicles": "N/A (Kẹt xe)", "counts": {}})
            
            # --- VẼ THÔNG BÁO KẸT XE LÊN ẢNH ---
            # Vẽ một hình chữ nhật nền cho chữ dễ đọc
            cv2.rectangle(frame_yolo, (0, 0), (350, 60), color, -1) 
            cv2.putText(frame_yolo, f"STATUS: {status}", (10, 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(frame_yolo, f"CONF: {conf:.2f}%", (10, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            # Chạy YOLO
            # Lưu ý: Hàm ai.detect của bạn nên trả về frame đã được vẽ box
            # Nếu ai.detect chưa trả về frame, bạn cần chỉnh lại hàm đó để nó return (result, total, annotated_frame)
            yolo_res, total = self.ai.detect(frame_yolo, brightness)
            
            # Nếu yolo_res có chứa frame đã vẽ (thường nằm trong yolo_res['annotated_frame'])
            # thì ta dùng frame đó, nếu không ta vẽ đè trạng thái "Thong thoang" lên frame_yolo
            total_sec, cmd = self.calculate_signal(total)
            result.update(yolo_res)
            
            # Vẽ trạng thái "Thông thoáng" nhỏ ở góc để biết CNN vẫn đang chạy
            cv2.putText(frame_yolo, f"CNN: {status} ({conf:.1f}%)", (10, frame_yolo.shape[0] - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 4. Finalize
        result.update({"total_seconds": total_sec, "green_seconds": max(0, total_sec - 3)})
        
        # Mã hóa frame đã được vẽ (annotated frame) để gửi lên Web
        _, buf = cv2.imencode('.jpg', frame_yolo)
        result['input_image'] = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"
        
        self.uart.send(cmd)
        return result, cmd

    def calculate_signal(self, total):
        if total < 5: return 20, "m1"
        elif total <= 10: return 45, "m2"
        elif total <= 20: return 60, "m3"
        return 90, "m4"