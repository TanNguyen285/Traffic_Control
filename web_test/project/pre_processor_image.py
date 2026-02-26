import cv2
import numpy as np
import torch
import os
from PIL import Image
import torchvision.transforms as transforms
from model_sci import Finetunemodel


class Tienxulyanh:
    def __init__(self, target_size=(640, 640), use_sci=True):
        self.target_size = target_size
        self.use_sci = use_sci
        self.brightness = 0.0
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        self.transform = transforms.ToTensor()

        if self.use_sci:
            try:
                model_path = "SCI/CVPR/weights/medium.pt"

                if os.path.exists(model_path):
                    self.sci_net = Finetunemodel(model_path).to(self.device).eval()
                    print(f"✅ Loaded SCI model trên {self.device}")
                else:
                    print(f"⚠️ Không tìm thấy weight tại {model_path}")
                    self.use_sci = False

            except Exception as e:
                print(f"⚠️ Lỗi load SCI model: {e}")
                self.use_sci = False

    # ================= LETTERBOX =================

    def letterbox(self, img, new_shape=(640, 640), color=(114, 114, 114)):
        shape = img.shape[:2]

        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))

        dw = (new_shape[1] - new_unpad[0]) / 2
        dh = (new_shape[0] - new_unpad[1]) / 2

        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

        top = int(round(dh - 0.1))
        bottom = int(round(dh + 0.1))
        left = int(round(dw - 0.1))
        right = int(round(dw + 0.1))

        return cv2.copyMakeBorder(
            img, top, bottom, left, right,
            cv2.BORDER_CONSTANT, value=color
        )

    # ================= BRIGHTNESS =================

    def _calculate_brightness(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return np.mean(hsv[:, :, 2]) / 255.0

    # ================= SCI ENHANCE =================

    def _apply_sci(self, frame):
        try:
            # Convert BGR → RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert sang PIL giống MemoryFriendlyLoader
            pil_img = Image.fromarray(rgb)

            # ToTensor giống dataset của bạn
            tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                _, r = self.sci_net(tensor)

            enhanced = r[0].permute(1, 2, 0).cpu().numpy()
            enhanced = np.clip(enhanced, 0, 1)
            enhanced = (enhanced * 255).astype(np.uint8)

            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR)

            return enhanced_bgr

        except Exception as e:
            print(f"⚠️ Lỗi xử lý SCI: {e}")
            return frame

    # ================= MAIN PROCESS =================

    def process(self, frame, roi_box=None):
        if frame is None:
            return None, 0.0

        # 1️⃣ Crop ROI
        if roi_box is not None:
            h, w = frame.shape[:2]
            y1, y2, x1, x2 = roi_box
            frame = frame[int(h*y1):int(h*y2), int(w*x1):int(w*x2)]

        # 2️⃣ Brightness
        self.brightness = self._calculate_brightness(frame)

        # 3️⃣ SCI
        if self.use_sci and self.brightness < 0.4:
            frame = self._apply_sci(frame)

        # 4️⃣ Letterbox cho YOLO
        frame = self.letterbox(frame, self.target_size)

        return frame, self.brightness

    # ================= PROCESS FILE =================

    def process_image_file(self, image_path, roi_box=None):
        try:
            frame = cv2.imread(image_path)

            if frame is None:
                return None, 0.0, False

            processed_frame, brightness = self.process(frame, roi_box)

            return processed_frame, brightness, True

        except Exception as e:
            print(f"❌ Lỗi xử lý file: {e}")
            return None, 0.0, False