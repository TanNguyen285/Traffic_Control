import cv2
import numpy as np
import torch
import os
from PIL import Image
import torchvision.transforms as transforms
from model_sci import Finetunemodel

class Tienxulyanh:
    def __init__(self, target_size=(640, 640), use_sci=True, sci_model_path=None):
        self.target_size = target_size
        self.use_sci = use_sci
        self.brightness = 0.0
        self.device = torch.device('cpu') 
        self.transform = transforms.ToTensor()
        self.sci_net = None

        # Khởi tạo SCI model nếu được yêu cầu và có đường dẫn
        if self.use_sci and sci_model_path:
            try:
                if os.path.exists(sci_model_path):
                    self.sci_net = Finetunemodel(sci_model_path).to(self.device).eval()
                    print(f"✅ [SCI] Loaded model thành công từ: {sci_model_path}")
                else:
                    print(f"⚠️ [SCI] Không tìm thấy file weight tại: {sci_model_path}")
                    self.use_sci = False
            except Exception as e:
                print(f"❌ [SCI] Lỗi khi load model: {e}")
                self.use_sci = False

    def _calculate_brightness(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return np.mean(hsv[:, :, 2]) / 255.0

    def _apply_sci(self, frame):
        if self.sci_net is None:
            return frame
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                _, r = self.sci_net(tensor)
            enhanced = r[0].permute(1, 2, 0).cpu().numpy()
            enhanced = np.clip(enhanced, 0, 1)
            enhanced = (enhanced * 255).astype(np.uint8)
            return cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️ Lỗi xử lý SCI: {e}")
            return frame

    def process_dual(self, frame, roi_box=None):
        if frame is None:
            return None, None, 0.0

        # 1. Crop vùng quan tâm (ROI)
        if roi_box is not None:
            h, w = frame.shape[:2]
            y1, y2, x1, x2 = roi_box
            frame = frame[int(h*y1):int(h*y2), int(w*x1):int(w*x2)]

        # 2. Xử lý thiếu sáng bằng SCI
        self.brightness = self._calculate_brightness(frame)
        if self.use_sci and self.brightness < 0.4:
            frame = self._apply_sci(frame)

        # 3. Resize cho CNN (224x224)
        frame_cnn = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_LINEAR)

        # 4. Resize cho YOLO (640x640) giữ nguyên tỉ lệ
        frame_yolo = self.letterbox(frame, self.target_size)

        return frame_cnn, frame_yolo, self.brightness

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114)):
        shape = img.shape[:2]
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw = (new_shape[1] - new_unpad[0]) / 2
        dh = (new_shape[0] - new_unpad[1]) / 2
        
        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)