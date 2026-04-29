import torch
import numpy as np
import time
import os
import sys

# --- [AUTO-FIX] CẤU HÌNH ĐƯỜNG DẪN DỰ ÁN ---
current_file_path = os.path.dirname(os.path.abspath(__file__))
# Lùi 2 cấp từ Service_Pi5/benchmark về Traffic_Control
project_root = os.path.abspath(os.path.join(current_file_path, "../../"))

if project_root not in sys.path:
    sys.path.append(project_root)

# Tự động đăng ký tất cả folder con (web_test, SimpleCNN, v.v.) vào hệ thống
for root, dirs, files in os.walk(project_root):
    if root not in sys.path:
        sys.path.append(root)
# ------------------------------------------

from ultralytics import YOLO
from benchmark.benchmark_engine import UnifiedBenchmark
from web_test.SimpleCNN.custom import SimpleCNN 
from web_test.model_sci import Finetunemodel

tester = UnifiedBenchmark()

# --- CẤU HÌNH ĐƯỜNG DẪN MODEL (Tính từ Traffic_Control) ---
SCI_P  = "web_test/weights/difficult.pt"
CNN_P  = "runs/exp3/best_cnn_model.pth"
YOLO_PT_P   = "runs/detect/yolov26_epoch50/weights/best.pt"
YOLO_NCNN_P = "runs/detect/best_ncnn_model"

def run_combined_test(sci_rel_path, model_rel_path, label, mode="YOLO"):
    """
    Hàm gộp tổng quát: 
    mode="YOLO" nếu chạy SCI + YOLO
    mode="CNN"  nếu chạy SCI + SimpleCNN
    """
    sci_full = os.path.join(project_root, sci_rel_path)
    mod_full = os.path.join(project_root, model_rel_path)
    
    if not os.path.exists(sci_full) or not os.path.exists(mod_full):
        print(f"❌ Lỗi đường dẫn: {sci_full} hoặc {mod_full} không tồn tại!")
        return

    print(f"[*] Đang test Gộp: {label}...")
    
    # Khởi tạo model
    sci_model = Finetunemodel(weights=sci_full).to(tester.device).eval()
    
    if mode == "YOLO":
        other_model = YOLO(mod_full)
    else:
        other_model = SimpleCNN(num_classes=2).to(tester.device)
        other_model.load_state_dict(torch.load(mod_full, map_location=tester.device))
        other_model.eval()

    dummy = torch.randn(1, 3, 480, 480).to(tester.device)
    times = []

    with torch.no_grad():
        # Warmup
        for _ in range(5):
            _, r = sci_model(dummy)
            if mode == "YOLO":
                img = (r.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
                other_model.predict(img, verbose=False)
            else:
                input_cnn = torch.nn.functional.interpolate(r, size=(224, 224))
                other_model(input_cnn)

        # Đo thực tế
        for _ in range(50):
            t0 = time.time()
            
            # BƯỚC 1: SCI làm rõ ảnh
            _, r = sci_model(dummy)
            
            # BƯỚC 2: Xử lý trung gian và chạy Model tiếp theo
            if mode == "YOLO":
                # Tensor (0-1) -> Numpy (0-255) cho YOLO
                img = (r.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
                other_model.predict(img, verbose=False)
            else:
                # Resize cho CNN
                input_cnn = torch.nn.functional.interpolate(r, size=(224, 224))
                other_model(input_cnn)
            
            if tester.device == "cuda": torch.cuda.synchronize()
            times.append((time.time() - t0) * 1000)

    avg = np.mean(times)
    tester.save_to_json(label, avg, 1000/avg, "(480->Input)")

if __name__ == "__main__":
    # --- CHẠY CÁC CASE KẾT HỢP ---
    # 2. SCI + YOLO (NCNN)
    run_combined_test(SCI_P, YOLO_NCNN_P, "SCI+Yolo_NCNN", mode="YOLO")
    
    # 3. SCI + SimpleCNN
    #run_combined_test(SCI_P, CNN_P, "SCI+SimpleCNN", mode="CNN")