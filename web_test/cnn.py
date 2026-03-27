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
        """ Dự đoán trạng thái từ frame (thường là 224x224) """
        if self.net is None: 
            return "N/A", 0.0, 0
        
        # Chuyển đổi sang định dạng PIL cho transform của PyTorch
        rgb = cv2.cvtColor(frame_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        
        # Tiền xử lý và đưa vào Model
        input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.net(input_tensor)
            probs = F.softmax(outputs, dim=1)[0]
            idx = torch.argmax(probs).item()
            conf = probs[idx].item() * 100
            
        return self.classes[idx], conf, idx