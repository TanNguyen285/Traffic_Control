import cv2
import numpy as np
import torch
import torch.nn as nn
import os
import model 

class Tienxulyanh:
    def __init__(self, target_size=(640, 640), use_dce=True):
        self.target_size = target_size
        self.use_dce = use_dce
        self.brightness = 0.0
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if self.use_dce:
            self.scale_factor = 12 # Zero-DCE++ yêu cầu kích thước chia hết cho số này
            self.dce_net = model.enhance_net_nopool(self.scale_factor).to(self.device)
            try:
                model_path = 'Zero-DCE++/Epoch99.pth'
                if os.path.exists(model_path):
                    self.dce_net.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
                    self.dce_net.eval()
                    print(f"✅ Loaded DCE model trên {self.device}")
                else:
                    print(f"⚠️ Không tìm thấy weight tại {model_path}, tắt DCE.")
                    self.use_dce = False
            except Exception as e:
                print(f"⚠️ Lỗi load model: {e}")
                self.use_dce = False

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114)):
        """Hàm giữ nguyên tỷ lệ ảnh để YOLO không bị nhận diện sai"""
        shape = img.shape[:2] 
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = (new_shape[1] - new_unpad[0]) / 2, (new_shape[0] - new_unpad[1]) / 2

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

    def _calculate_brightness(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return np.mean(hsv[:, :, 2]) / 255.0

    def _apply_dce(self, frame):
        """Fix lỗi Size Mismatch bằng cách crop ảnh chia hết cho scale_factor"""
        try:
            h, w = frame.shape[:2]
            # Ép kích thước ảnh phải chia hết cho scale_factor (12)
            h_new = (h // self.scale_factor) * self.scale_factor
            w_new = (w // self.scale_factor) * self.scale_factor
            
            if h != h_new or w != w_new:
                frame = frame[:h_new, :w_new, :]

            frame_norm = (frame / 255.0).astype(np.float32)
            frame_tensor = torch.from_numpy(frame_norm).to(self.device).permute(2, 0, 1).unsqueeze(0)
            
            with torch.no_grad():
                # Mô hình Zero-DCE++ trả về ảnh đã được nội suy lại đúng kích thước
                enhanced, _ = self.dce_net(frame_tensor)
            
            enhanced = enhanced.squeeze(0).permute(1, 2, 0).cpu().numpy()
            return np.clip(enhanced * 255, 0, 255).astype(np.uint8)
            
        except Exception as e:
            print(f"⚠️ Lỗi xử lý DCE chuyên sâu: {e}")
            return frame

    def process(self, frame, roi_box=None):
        if frame is None: return None, 0.0

        # 1. Cắt ROI trước 
        if roi_box is not None:
            h, w = frame.shape[:2]
            y1, y2, x1, x2 = roi_box
            frame = frame[int(h*y1):int(h*y2), int(w*x1):int(w*x2)]

        # 2. Tính độ sáng trên vùng ROI
        self.brightness = self._calculate_brightness(frame)
        
        # 3. Áp dụng DCE (Tăng sáng) TRƯỚC KHI letterbox
        # Vì DCE++ nhạy cảm với kích thước, ta xử lý nó trên ảnh gốc/ROI đã crop chuẩn
        if self.use_dce and self.brightness < 0.4: 
            frame = self._apply_dce(frame)

        # 4. Cuối cùng mới Letterbox về 640x640 cho YOLO
        frame = self.letterbox(frame, self.target_size)

        return frame, self.brightness

    def process_image_file(self, image_path, roi_box=None):
        try:
            frame = cv2.imread(image_path)
            if frame is None: return None, 0.0, False
            processed_frame, brightness = self.process(frame, roi_box)
            return processed_frame, brightness, True
        except Exception as e:
            print(f"❌ Lỗi xử lý file: {e}")
            return None, 0.0, False