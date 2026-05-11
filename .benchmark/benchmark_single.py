import torch
import numpy as np
import time
import os
import sys
import json
import cv2 # Cần cho ONNX (hoặc dùng numpy trực tiếp)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Sau đó mới đến dòng import của bạn
from benchmark.Model_benchmark.Simple_CNN import Simple_CNN
# =========================================================
# PATH FIX
# =========================================================
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, "../")) 

if project_root not in sys.path:
    sys.path.append(project_root)

for root, dirs, files in os.walk(project_root):
    if root not in sys.path:
        sys.path.append(root)

# =========================================================
# IMPORT
# =========================================================
from ultralytics import YOLO
from benchmark.Model_benchmark.Simple_CNN import Simple_CNN
from benchmark.Model_benchmark.Simple_Anpha import Simple_GLKA as Simple_Anpha
from benchmark.Model_benchmark.Simple_GLKA import Simple_GLKA
from benchmark.Model_benchmark.model_sci import Finetunemodel

# =========================================================
# DEVICE & JSON SAVE
# =========================================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
RESULT_FILE = os.path.join(project_root, "benchmark_results.json")

def save_result(data):
    all_data = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, "r") as f:
            try: all_data = json.load(f)
            except: all_data = []
    all_data.append(data)
    with open(RESULT_FILE, "w") as f:
        json.dump(all_data, f, indent=4)

# =========================================================
# CORE
# =========================================================
def run_single(relative_path, label):
    full_path = os.path.join(project_root, relative_path)
    if not os.path.exists(full_path):
        print(f"❌ Không tìm thấy model: {full_path}")
        return

    p = full_path.lower()
    l = label.lower()
    m_type = "Unknown"
    size = (224, 224)
    onnx_session = None

    # =========================
    # LOAD MODEL LOGIC
    # =========================
    # 1. SCI / Difficult Model
    if "sci" in p or "difficult" in p:
        model = Finetunemodel(weights=full_path).to(DEVICE).eval()
        m_type, size = "SCI", (480, 480)

    # 2. ONNX Models (CNN, GLKA, Anpha)
    elif p.endswith(".onnx"):
        import onnxruntime as ort
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if DEVICE == "cuda" else ['CPUExecutionProvider']
        onnx_session = ort.InferenceSession(full_path, providers=providers)
        m_type, size = "ONNX", (224, 224)
        model = None 

    # 3. YOLO Models (.pt hoặc NCNN folder)
    elif p.endswith(".pt") and "yolo" in l:
        model = YOLO(full_path)
        m_type, size = "YOLO_PT", (480, 480)
        
    elif os.path.isdir(full_path) or p.endswith(".ncnn"):
        model = YOLO(full_path)
        m_type, size = "YOLO_NCNN", (480, 480)

    # 4. Standard PyTorch (.pth)
    elif p.endswith(".pth"):
        if "glka" in l:
            model = Simple_GLKA(num_classes=2).to(DEVICE)
            m_type = "GLKA"
        elif "anpha" in l:
            model = Simple_Anpha(num_classes=2).to(DEVICE)
            m_type = "Anpha"
        else:
            model = Simple_CNN(num_classes=2).to(DEVICE)
            m_type = "SimpleCNN"
        
        model.load_state_dict(torch.load(full_path, map_location=DEVICE))
        model.eval()
        size = (224, 224)

    print(f"\n🚀 Test: {label} ({m_type}) | Device: {DEVICE}")

    # =========================
    # PREPARE INPUT (FIXED)
    # =========================
    if m_type == "ONNX":
        input_name = onnx_session.get_inputs()[0].name
        # Sửa np.randn thành np.random.randn
        dummy = np.random.randn(1, 3, *size).astype(np.float32)
    elif "YOLO" in m_type:
        # Giữ nguyên vì np.zeros là chuẩn
        dummy = np.zeros((*size, 3), dtype=np.uint8)
    else:
        # PyTorch thì dùng torch.randn là đúng
        dummy = torch.randn(1, 3, *size).to(DEVICE)

    # =========================
    # BENCHMARK FUNCTION
    # =========================
    def inference():
        if m_type == "ONNX":
            onnx_session.run(None, {input_name: dummy})
        elif "YOLO" in m_type:
            model.predict(dummy, verbose=False)
        else:
            model(dummy)

    # Warmup
    for _ in range(10): inference()

    # Measure
    times = []
    with torch.no_grad():
        for _ in range(50):
            if DEVICE == "cuda": torch.cuda.synchronize()
            t0 = time.perf_counter()
            
            inference()
            
            if DEVICE == "cuda": torch.cuda.synchronize()
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)

    # =========================
    # RESULTS
    # =========================
    times = np.array(times)
    avg, std, p95 = np.mean(times), np.std(times), np.percentile(times, 95)
    fps = 1000 / avg

    print(f"   >> {avg:.2f} ms | {fps:.2f} FPS")

    save_result({
        "label": label, "type": m_type, "device": DEVICE,
        "mean_ms": float(avg), "std": float(std), "p95": float(p95),
        "fps": float(fps), "input_size": size
    })

# =========================================================
# RUN ALL
# =========================================================
if __name__ == "__main__":
    test_cases = [
        # --- YOLO ---
        ("runs/Yolo/best.pt", "YOLO_PT"),
        ("runs/Yolo/best_ncnn_model", "YOLO_NCNN"),

        # --- PYTORCH (.pth) ---
        ("runs/CNN/best_acc.pth", "SimpleCNN_PTH"),
        ("runs/Anpha/best_acc.pth", "Anpha_PTH"),
        ("runs/GLKA/best_acc.pth", "GLKA_PTH"),

        # --- ONNX ---
        ("runs/CNN/simple_cnn.onnx", "SimpleCNN_ONNX"),
        ("runs/Anpha/simple_anpha.onnx", "Anpha_ONNX"),
        ("runs/GLKA/simple_glka.onnx", "GLKA_ONNX"),

        # --- SPECIAL ---
        ("runs/SCI/difficult.pt", "SCI"),
    ]

    for path, label in test_cases:
        run_single(path, label)

    print(f"\n✅ DONE → Results saved at: {RESULT_FILE}")