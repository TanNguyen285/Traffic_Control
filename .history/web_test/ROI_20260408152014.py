import cv2
import numpy as np

class ROIManager:
    def __init__(self, polygon_pts=None):
        """
        polygon_pts: Danh sách các điểm [x, y] tạo thành vùng quan sát.
        Nếu None, sẽ mặc định là một đa giác mẫu.
        """
        if polygon_pts is None:
            # Tọa độ mặc định (ví dụ cho khung hình 640x640)
            self.polygon_pts = np.array([
                [0, 640], [0, 250], [320, 180], [640, 250], [640, 640]
            ], np.int32)
        else:
            self.polygon_pts = np.array(polygon_pts, np.int32)
            
        self.polygon_pts = self.polygon_pts.reshape((-1, 1, 2))
        self.mask = None

    def apply_roi(self, frame):
        """Che ảnh gốc, chỉ giữ lại vùng trong đa giác (Polygon)"""
        if self.mask is None or self.mask.shape[:2] != frame.shape[:2]:
            h, w = frame.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(self.mask, [self.polygon_pts], 255)
        
        # Áp dụng mặt nạ
        res = cv2.bitwise_and(frame, frame, mask=self.mask)
        return res

    def draw_visual_roi(self, frame, alpha=0.3):
        """Vẽ vùng ROI màu xanh mờ lên ảnh để hiển thị lên Web debug"""
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.polygon_pts], (0, 255, 0)) # Màu xanh lá
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)