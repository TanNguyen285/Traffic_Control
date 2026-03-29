import cv2
import numpy as np
import torch
import os
from PIL import Image
import torchvision.transforms as transforms
from model_sci import Finetunemodel

class Tienxulyanh:
    def __init__(self, sci_path, target_size=(640, 640), use_sci=True):
        # --- CẤU HÌNH NHẬN TỪ BÊN NGOÀI ---
        self.target_size = target_size
        self.use_sci = use_sci
        self.device = torch.device('cpu')
        self.transform = transforms.ToTensor()
        
        # Tọa độ ROI cố định (Bạn chỉnh ở đây)
        self.y1, self.y2 = 150, 450
        self.x1, self.x2 = 0, 640
        
        # Load SCI Model dùng path truyền vào
        if self.use_sci:
            try:
                if os.path.exists(sci_path):
                    self.sci_net = Finetunemodel(sci_path).to(self.device).eval()
                    print(f"✅ SCI Loaded từ: {sci_path}")
                else:
                    print(f"⚠️ Không tìm thấy file SCI tại: {sci_path}")
                    self.use_sci = False
            except Exception as e:
                print(f"⚠️ Lỗi load SCI: {e}")
                self.use_sci = False

    def ttanhsang(self, frame):
        # Chuyển qua HSV lấy kênh V (Value) để tính độ sáng trung bình
        hsv_v = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 2]
        return np.mean(hsv_v) / 255.0

    def _apply_sci(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                _, r = self.sci_net(tensor)
            enhanced = r[0].permute(1, 2, 0).cpu().numpy()
            enhanced = (np.clip(enhanced, 0, 1) * 255).astype(np.uint8)
            return cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR)
        except:
            return frame

    def process_dual(self, frame, skip_roi=False):
        if frame is None: return None, None, 0.0

        # 1. CROP ROI (Chỉ thực hiện nếu KHÔNG PHẢI ảnh upload)
        if not skip_roi:
            frame_roi = frame[self.y1:self.y2, self.x1:self.x2]
        else:
            frame_roi = frame # Giữ nguyên khung hình nếu upload

        # 2. Tính độ sáng & SCI
        self.brightness = self._calculate_brightness(frame_roi)
        if self.use_sci and self.brightness < 0.4:
            frame_roi = self._apply_sci(frame_roi)

        # 3. Tạo ảnh cho CNN (224x224)
        frame_cnn = cv2.resize(frame_roi, (224, 224), interpolation=cv2.INTER_LINEAR)

        # 4. Tạo ảnh cho YOLO (640x640) - Luôn dùng letterbox để bù padding
        frame_yolo = self.letterbox(frame_roi, self.target_size)

        return frame_cnn, frame_yolo, self.brightness

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114)):
        shape = img.shape[:2] # [cao, rộng]
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))

        dw = (new_shape[1] - new_unpad[0]) / 2 # bù chiều ngang
        dh = (new_shape[0] - new_unpad[1]) / 2 # bù chiều dọc

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        
        return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)