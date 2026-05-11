import cv2
import numpy as np
import torch
from PIL import Image
import torchvision.transforms as transforms
from model_sci import Finetunemodel
from ROI import ROIManager # Import file mới tách

class Tienxulyanh:
    def __init__(self, sci_path, target_size=(480, 480), use_sci=True, polygon_pts=None):
        self.target_size = target_size
        self.use_sci = use_sci
        self.device = torch.device('cpu')#pi
        self.transform = transforms.ToTensor()
        
        # Khởi tạo bộ quản lý ROI
        self.roi_manager = ROIManager(polygon_pts)
        
        # Load SCI Model
        self.sci_net = None
        if self.use_sci:
            try:
                self.sci_net = Finetunemodel(sci_path).to(self.device).eval()
                print(f"✅ SCI Loaded successfully from: {sci_path}")
            except Exception as e:
                self.use_sci = False
                print(f"❌ Lỗi load SCI từ '{sci_path}': {type(e).__name__}: {e}")
                print(f"   → SCI module sẽ bị tắt")
# tính giá trị ánh sáng để kích hoạt SCI nếu cần
    def ttanhsang(self, frame):
        hsv_v = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 2]
        return np.mean(hsv_v) / 255.0
# Áp dụng SCI nếu độ sáng thấp và chuẩn bị ảnh cho YOLO và CNN
    def module_sci(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                _, r = self.sci_net(tensor)
            
            enhanced = r[0].permute(1, 2, 0).cpu().numpy()
            enhanced = (np.clip(enhanced, 0, 1) * 255).astype(np.uint8)
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR)

            # --- GIẢM SÁNG TẠI ĐÂY ---
            # alpha: trọng số ảnh đã tăng sáng (0.0 -> 1.0)
            # Nếu alpha càng nhỏ, ảnh sẽ càng tối và giống ảnh gốc hơn.
            alpha = 0.65 
            result = cv2.addWeighted(enhanced_bgr, alpha, frame, 1 - alpha, 0)
            
            return result
        except Exception as e:
            print(f"Lỗi SCI: {e}")
            return frame
# Chuẩn bị ảnh cho YOLO và CNN, đồng thời tạo ảnh hiển thị lên Web/UI
    def input_yolo_cnn(self, frame, skip_roi=False, debug=True):
        if frame is None: return None, None, 0.0

        # --- LUỒNG CHO AI (Vẫn giữ che đen để AI chạy chuẩn) ---
        if not skip_roi:
            frame_ai = self.roi_manager.apply_roi(frame) # Che đen vùng ngoài
        else:
            frame_ai = frame.copy()

        # Tính độ sáng và SCI
        self.brightness = self.ttanhsang(frame_ai)
        if self.use_sci and self.brightness < 0.4:
            frame_ai = self.module_sci(frame_ai)

        # 1. Ảnh cho CNN (Dùng ảnh đã che đen, size nhỏ)
        frame_cnn = cv2.resize(frame_ai, (224, 224))

        # 2. Ảnh cho YOLO & Hiển thị Web (Dùng ảnh sạch hoàn toàn)
        # Thay vì vẽ vùng xanh, ta dùng thẳng frame_ai hoặc frame gốc tùy bạn
        frame_display = frame_ai 

        # Tạo ảnh cuối cùng (Đóng khung 640x640)
        frame_yolo = self.letterbox(frame_display, self.target_size)

        return frame_cnn, frame_yolo, self.brightness
    def letterbox(self, img, new_shape=(480, 480), color=(114, 114, 114)):
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