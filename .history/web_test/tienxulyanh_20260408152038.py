import cv2
import numpy as np
import torch
from PIL import Image
import torchvision.transforms as transforms
from model_sci import Finetunemodel
from ROI import ROIManager # Import file mới tách

class Tienxulyanh:
    def __init__(self, sci_path, target_size=(640, 640), use_sci=True, polygon_pts=None):
        self.target_size = target_size
        self.use_sci = use_sci
        self.device = torch.device('cpu')
        self.transform = transforms.ToTensor()
        
        # Khởi tạo bộ quản lý ROI
        self.roi_manager = ROIManager(polygon_pts)
        
        # Load SCI Model
        self.sci_net = None
        if self.use_sci:
            try:
                self.sci_net = Finetunemodel(sci_path).to(self.device).eval()
                print(f"✅ SCI Loaded")
            except:
                self.use_sci = False

    def ttanhsang(self, frame):
        hsv_v = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 2]
        return np.mean(hsv_v) / 255.0

    def module_sci(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                _, r = self.sci_net(tensor)
            enhanced = r[0].permute(1, 2, 0).cpu().numpy()
            enhanced = (np.clip(enhanced, 0, 1) * 255).astype(np.uint8)
            return cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR)
        except: return frame

    def input_yolo_cnn(self, frame, skip_roi=False, debug=True):
        if frame is None: return None, None, 0.0

        # 1. Xử lý ROI qua ROIManager
        if not skip_roi:
            frame_roi = self.roi_manager.apply_roi(frame)
        else:
            frame_roi = frame

        # 2. Tính độ sáng & SCI
        self.brightness = self.ttanhsang(frame_roi)
        if self.use_sci and self.brightness < 0.2:
            frame_roi = self.module_sci(frame_roi)

        # 3. Tạo ảnh cho CNN (224x224)
        frame_cnn = cv2.resize(frame_roi, (224, 224), interpolation=cv2.INTER_LINEAR)

        # 4. Tạo ảnh cho YOLO (640x640)
        frame_yolo = self.letterbox(frame_roi, self.target_size)
        
        # Nếu muốn thấy vùng ROI xanh xanh trên Web thì vẽ đè lên
        if debug and not skip_roi:
            frame_yolo = self.roi_manager.draw_visual_roi(frame_yolo)

        return frame_cnn, frame_yolo, self.brightness

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114)):
        # (Giữ nguyên hàm letterbox cũ của bạn)
        shape = img.shape[:2]
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw = (new_shape[1] - new_unpad[0]) / 2
        dh = (new_shape[0] - new_unpad[1]) / 2
        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)