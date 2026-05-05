import torch
import numpy as np
import time
import os
import sys
import argparse

# =========================================================
# PATH SETUP
# =========================================================
current_file_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_file_path, "../../"))

if project_root not in sys.path:
    sys.path.append(project_root)

for root, dirs, files in os.walk(project_root):
    if root not in sys.path:
        sys.path.append(root)

# =========================================================
# IMPORT MODEL
# =========================================================
from ultralytics import YOLO
from benchmark.benchmark_engine import UnifiedBenchmark
from benchmark.Model_benchmark.Simple_Anpha import Simple_GLKA
from benchmark.Model_benchmark.Simple_GLKA import Simple_GLKA
from benchmark.Model_benchmark.Simple_CNN import Simple_CNN
from benchmark.Model_benchmark.model_sci import Finetunemodel

tester = UnifiedBenchmark()

# =========================================================
# PATH CONFIG
# =========================================================
SCI_P  = "runs/SCI/difficult.pt"
CNN_P  = "runs/CNN/best_acc.pth"
GLKA_P = "runs/GLKA/best_acc.pth"
ANPHA_P = "runs/Anpha/best_acc.pth"
YOLO_NCNN_P = "runs/Yolo/best_ncnn_model"

# =========================================================
# SYSTEM STABILIZATION
# =========================================================
def setup_environment():
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"

    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

# =========================================================
# DEVICE
# =========================================================
def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"

def sync_device(device):
    if device == "cuda":
        torch.cuda.synchronize()

# =========================================================
# LOAD MODEL
# =========================================================
def load_backend_model(mode, path, device):
    if mode == "yolo":
        return YOLO(path)

    elif mode == "cnn":
        model = Simple_CNN(num_classes=2).to(device)

    elif mode == "glka":
        model = Simple_GLKA(num_classes=2).to(device)

    elif mode == "anpha":
        model = Simple_GLKA(num_classes=2).to(device)

    else:
        raise ValueError(f"❌ Mode không hợp lệ: {mode}")

    model.load_state_dict(torch.load(path, map_location=device))
    model.eval()
    return model

# =========================================================
# BACKEND EXECUTION
# =========================================================
def run_backend(r, model, mode):
    if mode == "yolo":
        img = (r.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
        model.predict(img, verbose=False)
    else:
        input_tensor = torch.nn.functional.interpolate(r, size=(224, 224))
        model(input_tensor)

# =========================================================
# BENCHMARK CORE
# =========================================================
def run_combined_test(sci_path, model_path, mode, label,
                      warmup=20, runs=200):

    setup_environment()
    device = get_device()

    print(f"\n🚀 Device: {device} | Mode: {mode}")

    sci_full = os.path.join(project_root, sci_path)
    mod_full = os.path.join(project_root, model_path)

    if not os.path.exists(sci_full) or not os.path.exists(mod_full):
        print("❌ Sai đường dẫn model")
        return

    # LOAD MODEL
    sci_model = Finetunemodel(weights=sci_full).to(device).eval()
    backend = load_backend_model(mode, mod_full, device)

    dummy = torch.randn(1, 3, 480, 480).to(device)

    # =========================
    # WARMUP
    # =========================
    print("🔥 Warmup...")
    with torch.no_grad():
        for _ in range(warmup):
            _, r = sci_model(dummy)
            run_backend(r, backend, mode)

    sync_device(device)

    # =========================
    # BENCHMARK
    # =========================
    print("⏱ Benchmarking...")
    times = []

    with torch.no_grad():
        for _ in range(runs):
            sync_device(device)
            t0 = time.perf_counter()

            _, r = sci_model(dummy)
            run_backend(r, backend, mode)

            sync_device(device)
            t1 = time.perf_counter()

            times.append((t1 - t0) * 1000)

    times = np.array(times)

    # =========================
    # STATS
    # =========================
    avg = np.mean(times)
    std = np.std(times)
    p50 = np.percentile(times, 50)
    p90 = np.percentile(times, 90)
    p95 = np.percentile(times, 95)
    p99 = np.percentile(times, 99)
    fps = 1000 / avg

    print(f"""
📊 RESULT ({label})
Device : {device}
Runs   : {runs}

Mean   : {avg:.2f} ms
Std    : {std:.2f}
P50    : {p50:.2f}
P90    : {p90:.2f}
P95    : {p95:.2f}
P99    : {p99:.2f}

FPS    : {fps:.2f}
""")

    tester.save_to_json(f"{label}_{device}", avg, fps, "(480->input)")

# =========================================================
# MODEL PATH SELECTOR
# =========================================================
def get_model_path(mode):
    if mode == "yolo":
        return YOLO_NCNN_P
    elif mode == "cnn":
        return CNN_P
    elif mode == "glka":
        return GLKA_P
    elif mode == "anpha":
        return ANPHA_P
    else:
        raise ValueError("Mode không hợp lệ")

# =========================================================
# MAIN CLI
# =========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", type=str, required=True,
                        choices=["yolo", "cnn", "glka", "anpha"])
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=20)

    args = parser.parse_args()

    model_path = get_model_path(args.mode)

    run_combined_test(
        SCI_P,
        model_path,
        mode=args.mode,
        label=f"SCI+{args.mode.upper()}",
        warmup=args.warmup,
        runs=args.runs
    )