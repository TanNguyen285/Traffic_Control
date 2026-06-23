import cv2
import numpy as np
import json
import os

DEFAULT_CONFIG_PATH = "roi_config.json"

# 8 điểm mặc định, lưu theo TỈ LỆ (0-1) so với chiều rộng/cao khung hình
# -> không phụ thuộc kích thước ảnh thực tế, chạy được ở mọi resolution
DEFAULT_POLYGON_RATIO = [
    (0.10, 0.30), (0.30, 0.15), (0.55, 0.10), (0.80, 0.15),
    (0.95, 0.35), (0.90, 0.70), (0.50, 0.90), (0.15, 0.70),
]


class ROIManager:
    def __init__(self, polygon_pts=None, config_path=DEFAULT_CONFIG_PATH):
        """
        polygon_pts : list toạ độ tuyệt đối [(x,y), ...] (8 điểm) — nếu truyền vào
                      sẽ ưu tiên dùng, GIỮ TƯƠNG THÍCH với code cũ.
        config_path : đường dẫn file json lưu điểm khi vẽ tay bằng roi_editor.py.
                      Nếu polygon_pts=None và file này tồn tại -> tự load.
                      Nếu cả 2 đều không có -> dùng 8 điểm mặc định theo tỉ lệ
                      khung hình (tự tính khi biết kích thước frame đầu tiên).
        """
        self.config_path = config_path
        self.mask = None

        if polygon_pts is not None:
            self.polygon_pts = self._to_np(polygon_pts)
        elif os.path.exists(config_path):
            self.polygon_pts = self._to_np(self._load_config(config_path))
            print(f"✅ ROI loaded từ file vẽ tay: {config_path}")
        else:
            self.polygon_pts = None  # sẽ tự tạo theo tỉ lệ trong apply_roi/draw_roi
            print("ℹ️ Chưa có ROI vẽ tay -> dùng 8 điểm mặc định theo tỉ lệ khung hình")

    @staticmethod
    def _to_np(pts):
        return np.array(pts, np.int32).reshape((-1, 1, 2))

    @staticmethod
    def _load_config(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["points"]

    def _default_pts_for_size(self, w, h):
        return [(int(rx * w), int(ry * h)) for rx, ry in DEFAULT_POLYGON_RATIO]

    def _ensure_pts(self, frame):
        if self.polygon_pts is None:
            h, w = frame.shape[:2]
            default_pts = self._default_pts_for_size(w, h)
            self.polygon_pts = self._to_np(default_pts)
            # Lưu thẳng ra file ngay lần đầu -> từ đây về sau roi_config.json
            # là nguồn duy nhất, sửa tay trong file hay qua nút "Vẽ ROI" đều
            # cùng ghi/đọc 1 chỗ, không cần tính lại theo tỉ lệ mỗi lần chạy.
            if not os.path.exists(self.config_path):
                self.save_points(default_pts)

    def set_points(self, pts):
        """Set điểm mới ngay trong runtime (vd: đang kéo thả ở UI) — chưa lưu file"""
        self.polygon_pts = self._to_np(pts)
        self.mask = None  # ép tính lại mask ở lần apply_roi tiếp theo

    def save_points(self, pts=None, path=None):
        """Lưu điểm hiện tại (hoặc pts truyền vào) ra file json để lần chạy sau tự load"""
        path = path or self.config_path
        if pts is not None:
            self.polygon_pts = self._to_np(pts)
        self.mask = None  # ép tính lại mask ngay với điểm mới, không đợi đổi resolution
        pts_list = self.polygon_pts.reshape(-1, 2).tolist()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"points": pts_list}, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu ROI vào: {path}")

    def apply_roi(self, frame):
        """Che đen hoàn toàn vùng ngoài đa giác để AI tập trung nội dung bên trong"""
        self._ensure_pts(frame)
        if self.mask is None or self.mask.shape[:2] != frame.shape[:2]:
            h, w = frame.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(self.mask, [self.polygon_pts], 255)

        return cv2.bitwise_and(frame, frame, mask=self.mask)

    def draw_roi(self, frame, alpha=0.3, color=(235, 206, 135)):
        """
        Overlay màu mờ lên vùng ROI để hiển thị UI/Web.
        Mặc định: xanh biển nhạt (light sky blue, BGR = (235, 206, 135))
        """
        self._ensure_pts(frame)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.polygon_pts], color)
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)