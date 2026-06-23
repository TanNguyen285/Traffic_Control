import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from model_sci import Finetunemodel
from ROI import ROIManager

# ─────────────────────────────────────────────────────────────────────────────
# TINH CHỈNH — chỉnh 1 số này
#   SCI_BOOST : nhân hệ số trên float [0,1] TRƯỚC khi clip → không vỡ nét
#               1.0 = đúng output gốc SCI
#               1.5 = sáng hơn 50%, giữ nét
#               2.0 = sáng gấp đôi
#               (vùng đã sáng sẽ clip tại 1.0 nhưng vùng tối được kéo đúng)
# ─────────────────────────────────────────────────────────────────────────────
SCI_BOOST = 1.5


class Tienxulyanh:
    def __init__(self, sci_path, target_size=(480, 480), use_sci=True,
                 polygon_pts=None, roi_manager=None):
        """
        roi_manager : truyền vào 1 ROIManager đã tạo sẵn (vd cùng instance với
                      ROI_lane trong app.py) để AI và web stream LUÔN dùng
                      chung 1 ROI — vẽ tay đổi ROI ở web là AI áp dụng ngay,
                      không cần restart.
                      Nếu không truyền (None) thì tự tạo riêng như cũ
                      (dùng polygon_pts/config mặc định) — chỉ nên dùng khi
                      chạy Tienxulyanh độc lập, không kèm app.py.
        """
        self.target_size = target_size
        self.use_sci     = use_sci
        self.device      = torch.device('cpu')  # pi
        self.transform   = transforms.ToTensor()
        self.roi_manager = roi_manager if roi_manager is not None else ROIManager(polygon_pts)

        self.sci_net = None
        if self.use_sci:
            try:
                self.sci_net = Finetunemodel(sci_path).to(self.device).eval()
                print(f"✅ SCI Loaded successfully from: {sci_path}")
            except Exception as e:
                self.use_sci = False
                print(f"❌ Lỗi load SCI từ '{sci_path}': {type(e).__name__}: {e}")
                print(f"   → SCI module sẽ bị tắt")

    # ─────────────────────────────────────────────────────────────────────────
    # ĐO ĐỘ SÁNG — kênh V của HSV, percentile 95 tránh lệch do vùng đen mask
    # ─────────────────────────────────────────────────────────────────────────
    def ttanhsang(self, frame):
        v_channel = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)[:, :, 2]
        return np.percentile(v_channel, 95) / 255.0

    # ─────────────────────────────────────────────────────────────────────────
    # SCI đúng theo tác giả:
    #   1. tensor float → model → lấy r (float [0,1])
    #   2. nhân SCI_BOOST TRÊN FLOAT trước khi clip → không vỡ nét
    #   3. clip [0,1] → *255 → uint8 (đúng save_images của tác giả)
    # ─────────────────────────────────────────────────────────────────────────
    def module_sci(self, frame):
        if self.sci_net is None:
            return frame
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_tensor = (torch.from_numpy(rgb)
                          .permute(2, 0, 1).float().div(255.0)
                          .unsqueeze(0).to(self.device))

            with torch.no_grad():
                _, r = self.sci_net(img_tensor)

            # Đúng logic tác giả: lấy r[0], transpose → float numpy
            image_numpy = r[0].cpu().float().numpy()           # (C, H, W)
            image_numpy = np.transpose(image_numpy, (1, 2, 0)) # (H, W, C)

            # Boost TRÊN FLOAT trước khi clip — giữ tỉ lệ sáng/tối, không vỡ nét
            image_numpy = image_numpy * SCI_BOOST

            # Clip và convert đúng như save_images của tác giả
            enhanced_rgb = np.clip(image_numpy * 255.0, 0, 255).astype(np.uint8)
            enhanced_bgr = cv2.cvtColor(enhanced_rgb, cv2.COLOR_RGB2BGR)
            return enhanced_bgr

        except Exception as e:
            print(f"⚠️ SCI Error: {e}")
            return frame

    # ─────────────────────────────────────────────────────────────────────────
    # PIPELINE CHÍNH
    # ─────────────────────────────────────────────────────────────────────────
    def input_yolo_cnn(self, frame, skip_roi=False, debug=True):
        if frame is None:
            return None, None, None, 0.0   # thêm None cho frame_enhanced

        if not skip_roi:
            roi_only        = self.roi_manager.apply_roi(frame.copy())
            self.brightness = self.ttanhsang(roi_only)
        else:
            self.brightness = self.ttanhsang(frame)

        frame_enhanced = frame.copy()
        if self.use_sci and self.brightness < 0.4:
            frame_enhanced = self.module_sci(frame)

        if not skip_roi:
            frame_ai = self.roi_manager.apply_roi(frame_enhanced)
        else:
            frame_ai = frame_enhanced

        frame_cnn  = cv2.resize(frame_ai, (224, 224))
        frame_yolo = self.letterbox(frame_ai, self.target_size)

        return frame_cnn, frame_yolo, frame_enhanced, self.brightness  # +frame_enhanced

    def letterbox(self, img, new_shape=(480, 480), color=(114, 114, 114)):
        shape     = img.shape[:2]
        r         = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
        dw        = (new_shape[1] - new_unpad[0]) / 2
        dh        = (new_shape[0] - new_unpad[1]) / 2
        if shape[::-1] != new_unpad:
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top,  bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right  = int(round(dw - 0.1)), int(round(dw + 0.1))
        return cv2.copyMakeBorder(img, top, bottom, left, right,
                                  cv2.BORDER_CONSTANT, value=color)