import torch
import numpy as np
import time
import os
import sys

# --- TỰ ĐỘNG FIX MỌI LỖI IMPORT ---
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, "../../"))

# Thêm tất cả các folder con của Traffic_Control vào path để tránh lỗi loss_sci, v.v.
if project_root not in sys.path:
    sys.path.append(project_root)
for root, dirs, files in os.walk(project_root):
    if root not in sys.path:
        sys.path.append(root)

from ultralytics import YOLO
from benchmark_engine import UnifiedBenchmark
from web_test.SimpleCNN.custom import SimpleCNN 
from web_test.model_sci import Finetunemodel

tester = UnifiedBenchmark()

def run_single(relative_path, label):
    full_path = os.path.join(project_root, relative_path)
    if not os.path.exists(full_path):
        print(f"❌ Không tìm thấy model tại: {full_path}")
        return

    p = full_path.lower()
    
    # 1. Nhận diện SCI
    if "sci" in p or "difficult" in p:
        model = Finetunemodel(weights=full_path).to(tester.device).eval()
        m_type, size = "SCI", (640, 640)
    
    # 2. Nhận diện SimpleCNN (.pth)
    elif p.endswith(".pth"):
        model = SimpleCNN(num_classes=2).to(tester.device)
        model.load_state_dict(torch.load(full_path, map_location=tester.device))
        model.eval()
        m_type, size = "CNN", (160, 160)
    
    # 3. Nhận diện YOLO (Cả .pt và folder ncnn)
    else:
        # YOLO tự động hiểu nếu đưa vào path folder chứa ncnn hoặc file .pt
        model = YOLO(full_path)
        m_type, size = "YOLO", (640, 640)

    print(f"[*] Đang test: {label} ({m_type})...")
    
    # Chuẩn bị dummy input
    dummy = torch.randn(1, 3, *size).to(tester.device) if m_type != "YOLO" else np.zeros((*size, 3), dtype=np.uint8)
    
    # Warmup
    for _ in range(5):
        _ = model.predict(dummy, verbose=False) if m_type == "YOLO" else model(dummy)

    times = []
    with torch.no_grad():
        for _ in range(50):
            t0 = time.time()
            if m_type == "YOLO": 
                model.predict(dummy, verbose=False)
            else: 
                model(dummy)
            if tester.device == "cuda": torch.cuda.synchronize()
            times.append((time.time() - t0) * 1000)
    
    avg = np.mean(times)
    tester.save_to_json(label, avg, 1000/avg, size)

if __name__ == "__main__":
    # CHẠY ĐƠN LẺ TỪNG THẰNG
    run_single("web_test/weights/difficult.pt", "SCI")
    
    # Test YOLO .pt chuẩn
    #run_single("runs/detect/yolov26_epoch50/weights/best.pt", "Yolo_PT")
    
    # Test YOLO NCNN (Đưa đường dẫn đến cái FOLDER chứa các file ncnn)
    #run_single("runs/detect/best_ncnn_model", "Yolo_NCNN")
    
    # run_single("runs/exp3/best_cnn_model.pth", "SimpleCNN")