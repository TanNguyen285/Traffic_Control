import torch
import numpy as np
import time
import os
import sys

# --- TỰ ĐỘNG FIX MỌI LỖI IMPORT ---
# --- FIX ĐƯỜNG DẪN GỐC ---
current_file_path = os.path.dirname(os.path.abspath(__file__))
# Nếu benchmark_single.py nằm trong folder 'benchmark', chỉ cần nhảy ra 1 cấp để về 'Traffic_Control'
project_root = os.path.abspath(os.path.join(current_file_path, "../")) 

# Kiểm tra thử cho chắc chắn
print(f"DEBUG: Project Root hiện tại là: {project_root}")

if project_root not in sys.path:
    sys.path.append(project_root)
for root, dirs, files in os.walk(project_root):
    if root not in sys.path:
        sys.path.append(root)

from ultralytics import YOLO
from benchmark.benchmark_engine import UnifiedBenchmark
# Import đúng theo cấu trúc folder và tên class khác nhau của ông
from benchmark.Model_benchmark.Simple_CNN import SimpleCNN
from benchmark.Model_benchmark.Simple_LKA import Simple_LKA
from benchmark.Model_benchmark.Simple_GLKA import Simple_GLKA
from benchmark.Model_benchmark.model_sci import Finetunemodel

tester = UnifiedBenchmark()

def run_single(relative_path, label):
    full_path = os.path.join(project_root, relative_path)
    if not os.path.exists(full_path):
        print(f"❌ Không tìm thấy model tại: {full_path}")
        return

    p = full_path.lower()
    l = label.lower()
    
    # Mặc định size
    m_type = "Unknown"
    size = (224, 224)
    
    # 1. Nhận diện SCI
    if "sci" in p or "difficult" in p:
        model = Finetunemodel(weights=full_path).to(tester.device).eval()
        m_type, size = "SCI", (480, 480)
    
    # 2. Nhận diện YOLO (Cả .pt và folder ncnn)
    elif p.endswith(".pt") or os.path.isdir(full_path):
        model = YOLO(full_path)
        m_type, size = "YOLO", (480, 480)

    # 3. Nhận diện các dòng CNN (.pth) - Khởi tạo dựa trên tên Class riêng biệt
    elif p.endswith(".pth"):
        if "glka" in l:
            model = Simple_GLKA(num_classes=2).to(tester.device)
            m_type = "GLKA"
        elif "lka" in l:
            model = Simple_LKA(num_classes=2).to(tester.device)
            m_type = "LKA"
        else:
            model = SimpleCNN(num_classes=2).to(tester.device)
            m_type = "SimpleCNN"
            
        model.load_state_dict(torch.load(full_path, map_location=tester.device))
        model.eval()
        size = (224, 224)

    print(f"[*] Đang test: {label} ({m_type}) | Device: {tester.device}...")
    
    # Chuẩn bị dummy input (Tensor cho CNN/SCI, Numpy cho YOLO)
    dummy = torch.randn(1, 3, *size).to(tester.device) if m_type != "YOLO" else np.zeros((*size, 3), dtype=np.uint8)
    
    # Warmup (10 vòng để GPU ổn định)
    for _ in range(10):
        _ = model.predict(dummy, verbose=False) if m_type == "YOLO" else model(dummy)

    times = []
    with torch.no_grad():
        for _ in range(50):
            t0 = time.time()
            if m_type == "YOLO": 
                model.predict(dummy, verbose=False)
            else: 
                model(dummy)
            
            if tester.device == "cuda": 
                torch.cuda.synchronize()
            
            times.append((time.time() - t0) * 1000)
    
    avg_ms = np.mean(times)
    fps = 1000 / avg_ms
    
    print(f"   >> Kết quả: {avg_ms:.2f} ms | {fps:.2f} FPS")
    tester.save_to_json(label, avg_ms, fps, size)

if __name__ == "__main__":
    # --- CHẠY TEST ---
    
    # 1. YOLO NCNN
    # run_single("runs/detect/best_ncnn_model", "Yolo_NCNN")
    #Test SCI
    #run_single("runs/SCI/difficult.pt", "SCI")

    # Test Simple CNN
    #run_single("runs/CNN/best_cnn_model.pth", "SimpleCNN")
    #run_single("runs/CNN/simple_cnn.onnx", "SimpleCNN_ONNX")

    # Test LKA
    run_single("runs/GLKA_345/best_cnn_model.pth", "GLKA_345")
    #run_single("runs/GLKA_345/simple_glka345.pth", "LKA")
    
    # Test GLKA
    #run_single("runs/GLKA_34/best_cnn_model.pth", "GLKA")
    #run_single("runs/GLKA_34/simple_glka34.onnx", "GLKA")
