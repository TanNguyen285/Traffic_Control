import torch
import torch.nn.functional as F
import cv2
from PIL import Image

class Simple_CNN_config:
    def __init__(self, model, transform, classes, device):
        self.net = model
        self.transform = transform
        self.classes = classes
        self.device = device

    def predict(self, frame_cv2):
        if self.net is None: 
            return "N/A", 0.0, 0
        
        rgb = cv2.cvtColor(frame_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        input_cnn = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.net(input_cnn)
            probs = F.softmax(outputs, dim=1)[0]
            idx = torch.argmax(probs).item()
            conf = probs[idx].item() * 100
            
        return self.classes[idx], conf, idx

    def draw_prediction(self, frame, label, conf):
        """ Vẽ text thông báo trạng thái lên frame """
        # Chọn màu: Đỏ cho Kẹt xe, Xanh lá cho Thoáng
        color = (0, 0, 255) if label == "Ket Xe" else (0, 255, 0)
        
        text = f"CNN: {label} ({conf:.1f}%)"
        
        # Vẽ nền đen cho chữ dễ đọc hơn (Background box)
        cv2.rectangle(frame, (10, 20), (350, 60), (0, 0, 0), -1)
        
        # Viết chữ lên ảnh
        cv2.putText(frame, text, (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        return frame