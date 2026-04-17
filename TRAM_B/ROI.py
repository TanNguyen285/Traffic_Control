import cv2
import numpy as np

class ROIManager:
    def __init__(self, polygon_pts): # Bỏ cái =None đi nếu muốn bắt buộc phải truyền từ Config
        self.polygon_pts = np.array(polygon_pts, np.int32).reshape((-1, 1, 2))
        self.mask = None

    def apply_roi(self, frame):
        """Che đen hoàn toàn vùng ngoài đa giác để AI tập trung nội dung bên trong"""
        if self.mask is None or self.mask.shape[:2] != frame.shape[:2]:
            h, w = frame.shape[:2]
            self.mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(self.mask, [self.polygon_pts], 255)
        
        return cv2.bitwise_and(frame, frame, mask=self.mask)

    def draw_roi(self, frame, alpha=0.3):
        """Tạo hiệu ứng xanh lá mờ lên vùng quan sát để hiển thị lên UI/Web"""
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.polygon_pts], (0, 255, 0)) # Màu xanh lá (B, G, R)
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)