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
    def ttanhsang(self, frame):
        # Chuyển sang ảnh xám để tính cho nhanh
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.percentile(gray, 95) / 255.0 
        
        return brightness
    def module_sci(self, frame):
        if self.sci_net is None:
            return frame
            
        try:
            # 1. Chuẩn bị Tensor (Tối ưu: Bỏ qua PIL, dùng thẳng Numpy)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).unsqueeze(0).to(self.device)
            # 2. Forward qua SCI
            with torch.no_grad():
                _, r = self.sci_net(img_tensor) 
            enhanced_numpy = r[0].permute(1, 2, 0).cpu().numpy()
            enhanced_bgr = cv2.cvtColor((np.clip(enhanced_numpy, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            # Công thức: Alpha chạy từ 0.8 (tối mịt) về 0.0 (đủ sáng)
            # Ngưỡng: dưới 0.1 lấy 0.8 SCI, trên 0.4 lấy 0.0 SCI (tắt)
            alpha = np.clip((0.4 - self.brightness) / 0.3 * 0.8, 0, 0.8)
            # 5. PHA TRỘN (Alpha Blending)
            # result = enhanced_bgr * alpha + frame * (1 - alpha)
            result = cv2.addWeighted(enhanced_bgr, alpha, frame, 1 - alpha, 0)
            return result

        except Exception as e:
            print(f"⚠️ SCI Error: {e}")
            return frame
        
    def input_yolo_cnn(self, frame, skip_roi=False, debug=True):
        if frame is None: return None, None, 0.0
        # 1. Tính độ sáng dựa trên vùng ROI để làm "ngưỡng" 
        # Nhưng tính trên frame gốc cắt theo mask để không bị màu đen của apply_roi làm sai lệch
        if not skip_roi:
            # Tạo một bản nháp chỉ để tính độ sáng vùng quan tâm
            roi_only = self.roi_manager.apply_roi(frame.copy()) 
            self.brightness = self.ttanhsang(roi_only)
        else:
            self.brightness = self.ttanhsang(frame)

        # 2. Xử lý làm sáng (Chạy trên TOÀN ẢNH GỐC để ánh sáng tự nhiên)
        frame_enhanced = frame.copy()
        if self.use_sci and self.brightness < 0.4:
            frame_enhanced = self.module_sci(frame) # Truyền frame gốc vào đây

        # 3. Sau khi làm sáng xong mới áp ROI (Che đen vùng ngoài)
        if not skip_roi:
            frame_ai = self.roi_manager.apply_roi(frame_enhanced)
        else:
            frame_ai = frame_enhanced

        # 4. Chuẩn bị đầu ra
        frame_cnn = cv2.resize(frame_ai, (224, 224))
        frame_yolo = self.letterbox(frame_ai, self.target_size)

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