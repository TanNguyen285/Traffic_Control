"""
🎯 Benchmark 6 YOLO Variants - Đo Precision, Recall, F1, mAP50, FPS
Models: yolov11_glka_trained, yolov11n_goc, yolov26_480, yolov26_640,
        yolov26_glka, yolov26_goc
Val set: C:/Users/ThisPC/Desktop/Dataset_Yolo+Congestion/Yolo/data_train/images/val
"""

import os
import sys
import json
import time
import gc
import platform
import numpy as np
import torch

from ultralytics import YOLO

# =========================================================
# PATHS
# =========================================================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

VAL_IMAGES   = r"C:\Users\ThisPC\Desktop\Dataset_Yolo+Congestion\Yolo\data_train\images\val"
VAL_LABELS   = r"C:\Users\ThisPC\Desktop\Dataset_Yolo+Congestion\Yolo\data_train\labels\val"
DATA_YAML    = r"C:\Users\ThisPC\Desktop\Dataset_Yolo+Congestion\Yolo\data_train\dataset.yaml"
RUNS_ROOT    = os.path.join(PROJECT_ROOT, "runs")
RESULT_FILE  = os.path.join(os.path.dirname(__file__), "yolo_benchmark_results.json")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Auto-detect params (giống CNN benchmark)
is_pi        = "aarch64" in platform.machine()
WARMUP_IMGS  = 20  if is_pi else 200    # Số ảnh warmup trước khi đo FPS
N_RUNS       = 1   if is_pi else 3     # Chạy val 3 lần, lấy median FPS
CONF_THRESH  = 0.25
IOU_THRESH   = 0.45

print(f"🖥️  Device : {DEVICE}")
if DEVICE == "cuda":
    print(f"   GPU   : {torch.cuda.get_device_name(0)}")
print(f"   Val   : {VAL_IMAGES}")
print(f"   Warmup: {WARMUP_IMGS} imgs  |  Runs: {N_RUNS}")

# =========================================================
# MODEL REGISTRY
# label → (folder_in_runs, input_size)
# input_size được suy từ tên folder (480/640)
# =========================================================
YOLO_REGISTRY = {
    "YOLOv11_GLKA"  : ("yolov11_glka_trained", 640),
    "YOLOv11n_GOC"  : ("yolov11n_goc",          640),
    "YOLOv26_480"   : ("yolov26_480",            480),
    "YOLOv26_640"   : ("yolov26_640",            640),
    "YOLOv26_GLKA"  : ("yolov26_glka",           640),
    "YOLOv26_GOC"   : ("yolov26_goc",            640),
}

# =========================================================
# HELPER: Lấy danh sách ảnh val
# =========================================================
def get_val_images(folder):
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    imgs = [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if os.path.splitext(f)[1].lower() in exts
    ]
    return imgs


# =========================================================
# HELPER: Đo FPS thực tế (inference only, không tính postprocess)
# Chạy từng ảnh batch=1 để mô phỏng realtime deploy
# =========================================================
def measure_fps(model, val_imgs, imgsz):
    """Warmup → đo latency từng ảnh → trả về mean_ms, fps"""

    # Warmup
    warmup_imgs = val_imgs[:WARMUP_IMGS]
    for p in warmup_imgs:
        model.predict(p, imgsz=imgsz, conf=CONF_THRESH, iou=IOU_THRESH,
                      device=DEVICE, verbose=False, stream=False)

    if DEVICE == "cuda":
        torch.cuda.synchronize()

    # Đo
    times = []
    for p in val_imgs:
        if DEVICE == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        model.predict(p, imgsz=imgsz, conf=CONF_THRESH, iou=IOU_THRESH,
                      device=DEVICE, verbose=False, stream=False)
        if DEVICE == "cuda":
            torch.cuda.synchronize()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)

    times = np.array(times)
    # Trim outlier 5-95
    lo, hi = np.percentile(times, 5), np.percentile(times, 95)
    t = times[(times >= lo) & (times <= hi)]
    return float(np.mean(t)), float(1000 / np.mean(t))


# =========================================================
# MAIN BENCHMARK
# =========================================================
def benchmark_yolo(label, folder, imgsz):

    weight_path = os.path.join(RUNS_ROOT, folder, "weights", "best.pt")

    if not os.path.exists(weight_path):
        print(f"❌  {label}: Không tìm thấy → {weight_path}")
        return None

    print(f"\n{'='*60}")
    print(f"⏱️  {label}  |  imgsz={imgsz}  |  {N_RUNS} runs")
    print(f"{'='*60}")

    # Clear cache
    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    # Load model
    try:
        model = YOLO(weight_path)
    except Exception as e:
        print(f"❌  {label}: Load lỗi → {e}")
        return None

    val_imgs = get_val_images(VAL_IMAGES)
    if not val_imgs:
        print(f"❌  Không tìm thấy ảnh trong {VAL_IMAGES}")
        return None

    print(f"   📂 Val images: {len(val_imgs)} ảnh")

    # ===================
    # BƯỚC 1: Đánh giá Precision / Recall / F1 / mAP
    # Dùng model.val() — chạy trên toàn bộ val set 1 lần
    # ===================
    print(f"   📊 Đang chạy val() để lấy metrics...")
    try:
        metrics = model.val(
            data=DATA_YAML,
            imgsz=imgsz,
            conf=CONF_THRESH,
            iou=IOU_THRESH,
            device=DEVICE,
            split="val",
            verbose=False,
            plots=False,
            save=False,
            save_json=False,
        )

        mp        = float(metrics.box.mp)         # mean Precision
        mr        = float(metrics.box.mr)         # mean Recall
        map50     = float(metrics.box.map50)      # mAP@0.5
        map50_95  = float(metrics.box.map)        # mAP@0.5:0.95
        f1        = float(2 * mp * mr / (mp + mr + 1e-8))

        # Per-class metrics (nếu có)
        per_class = {}
        if hasattr(metrics.box, "ap_class_index") and metrics.box.ap_class_index is not None:
            names = model.names  # dict {0: 'class0', ...}
            aps   = metrics.box.ap50   # array per class
            ps    = metrics.box.p      # precision per class
            rs    = metrics.box.r      # recall per class
            for idx, cls_id in enumerate(metrics.box.ap_class_index):
                cls_name = names.get(int(cls_id), f"cls{cls_id}")
                per_class[cls_name] = {
                    "precision": float(ps[idx]) if idx < len(ps) else 0.0,
                    "recall"   : float(rs[idx]) if idx < len(rs) else 0.0,
                    "ap50"     : float(aps[idx]) if idx < len(aps) else 0.0,
                }

        print(f"   ✅ mP={mp:.4f}  mR={mr:.4f}  F1={f1:.4f}  mAP50={map50:.4f}  mAP50-95={map50_95:.4f}")

    except Exception as e:
        print(f"   ❌ val() lỗi: {e}")
        return None

    # ===================
    # BƯỚC 2: Đo FPS thực tế (N_RUNS lần, lấy median)
    # ===================
    print(f"   ⚡ Đo FPS ({N_RUNS} runs × {len(val_imgs)} ảnh)...")
    all_means = []
    all_fps   = []

    for run_idx in range(N_RUNS):
        mean_ms, fps = measure_fps(model, val_imgs, imgsz)
        all_means.append(mean_ms)
        all_fps.append(fps)
        print(f"   Run {run_idx+1}: Mean={mean_ms:.2f}ms  FPS={fps:.2f}")
        if run_idx < N_RUNS - 1:
            time.sleep(2)

    final_mean_ms = float(np.median(all_means))
    final_fps     = float(np.median(all_fps))
    stability     = float(np.std(all_means))
    peak_mem      = float(torch.cuda.max_memory_allocated() / 1024 / 1024) if DEVICE == "cuda" else 0.0

    print(f"   → FPS Final : {final_fps:.2f}  Mean={final_mean_ms:.2f}ms  Stability=±{stability:.2f}ms")
    if peak_mem:
        print(f"   → Memory    : {peak_mem:.1f} MB")

    return {
        "label"      : label,
        "folder"     : folder,
        "imgsz"      : imgsz,
        "device"     : DEVICE,
        "n_val_imgs" : len(val_imgs),
        # Accuracy metrics
        "precision"  : mp,
        "recall"     : mr,
        "f1"         : f1,
        "map50"      : map50,
        "map50_95"   : map50_95,
        "per_class"  : per_class,
        # Speed metrics
        "mean_ms"    : final_mean_ms,
        "fps"        : final_fps,
        "stability"  : stability,
        "peak_mem_mb": peak_mem,
    }


# =========================================================
# RUN ALL 6 VARIANTS
# =========================================================
if __name__ == "__main__":

    print("\n" + "="*60)
    print("🎯 YOLO BENCHMARK - 6 VARIANTS")
    print("="*60)

    results = []
    for label, (folder, imgsz) in YOLO_REGISTRY.items():
        r = benchmark_yolo(label, folder, imgsz)
        if r:
            results.append(r)

    # ===================
    # SUMMARY TABLE
    # ===================
    if results:
        results_sorted = sorted(results, key=lambda x: x["map50"], reverse=True)

        print(f"\n{'='*75}")
        print("📊 SUMMARY - Sorted by mAP50")
        print(f"{'='*75}")
        print(f"{'Rank':<5}{'Model':<18}{'P':<8}{'R':<8}{'F1':<8}{'mAP50':<10}{'mAP50-95':<12}{'FPS':<8}{'Stab'}")
        print("-" * 75)
        for i, r in enumerate(results_sorted, 1):
            print(
                f"{i:<5}{r['label']:<18}"
                f"{r['precision']:<8.4f}{r['recall']:<8.4f}{r['f1']:<8.4f}"
                f"{r['map50']:<10.4f}{r['map50_95']:<12.4f}"
                f"{r['fps']:<8.1f}±{r['stability']:.2f}ms"
            )

        # Per-class detail
        print(f"\n{'='*75}")
        print("📋 PER-CLASS mAP50 DETAIL")
        print(f"{'='*75}")
        for r in results_sorted:
            print(f"\n  [{r['label']}]")
            if r["per_class"]:
                print(f"  {'Class':<20}{'Precision':<12}{'Recall':<10}{'AP50'}")
                print(f"  {'-'*50}")
                for cls, v in r["per_class"].items():
                    print(f"  {cls:<20}{v['precision']:<12.4f}{v['recall']:<10.4f}{v['ap50']:.4f}")
            else:
                print("  (Không có per-class data)")

        # Save JSON
        all_results = []
        if os.path.exists(RESULT_FILE):
            with open(RESULT_FILE) as f:
                try:
                    all_results = json.load(f)
                except Exception:
                    pass

        all_results.append({
            "timestamp" : time.strftime("%Y-%m-%d %H:%M:%S"),
            "device"    : DEVICE,
            "conf"      : CONF_THRESH,
            "iou"       : IOU_THRESH,
            "results"   : results_sorted,
        })
        with open(RESULT_FILE, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Saved → {RESULT_FILE}\n")