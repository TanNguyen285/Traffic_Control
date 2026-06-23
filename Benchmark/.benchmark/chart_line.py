"""
Unified CNN Benchmark - PyTorch + ONNX + YOLO (fair comparison)
YOLO tach thanh 3 sub-benchmark: full / pure inference / preprocess only
"""

import torch
import numpy as np
import time
import os, sys, json, gc
import subprocess

try:
    import onnxruntime as ort
except ImportError:
    print("⚠️  ONNX Runtime not installed (optional for ONNX benchmark)")
    ort = None


# =========================================================
# PLATFORM DETECTION
# =========================================================
def detect_platform():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Hardware"):
                    hw = line.split(":")[-1].strip()
                    if "BCM2712" in hw:
                        return "pi5"
                    if "BCM2711" in hw:
                        return "pi4"
    except Exception:
        pass
    if torch.cuda.is_available():
        return "gpu"
    return "cpu"

PLATFORM = detect_platform()
DEVICE   = "cuda" if PLATFORM == "gpu" else "cpu"

_PLATFORM_CFG = {
    "pi4": dict(WARMUP=20,  TEST=100,  N_RUNS=3, SLEEP=12),
    "pi5": dict(WARMUP=30,  TEST=150,  N_RUNS=3, SLEEP=8),
    "gpu": dict(WARMUP=500, TEST=2000, N_RUNS=5, SLEEP=5),
    "cpu": dict(WARMUP=50,  TEST=300,  N_RUNS=3, SLEEP=5),
}
cfg    = _PLATFORM_CFG[PLATFORM]
WARMUP = cfg["WARMUP"]
TEST   = cfg["TEST"]
N_RUNS = cfg["N_RUNS"]
SLEEP  = cfg["SLEEP"]
SIZE   = (224, 224)

# =========================================================
# SETUP PATHS
# =========================================================
current_dir  = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

ONNX_DIR    = os.path.join(project_root, "onnx_models")
RESULT_FILE = os.path.join(current_dir, "cnn_benchmark_results.json")

print("=" * 75)
print(f"🔬 UNIFIED CNN BENCHMARK - PyTorch + ONNX + YOLO (fair)")
print("=" * 75)
print(f"Platform : {PLATFORM.upper()}")
if PLATFORM == "gpu":
    print(f"GPU      : {torch.cuda.get_device_name(0)}")
if ort:
    print(f"ONNX RT  : Available (providers: {ort.get_available_providers()})")
else:
    print(f"ONNX RT  : Not installed (ONNX benchmark skipped)")
print(f"Config   : Warmup={WARMUP}, Test={TEST}, Runs={N_RUNS}, Sleep={SLEEP}s")
print("=" * 75)

# =========================================================
# IMPORT PYTORCH MODELS
# =========================================================
from Simple_CNN         import Simple_CNN
from Simple_Anpha_Plus  import Simple_GLKA as Simple_AnphaPlus
from Simple_Anphax      import Simple_GLKA as Simple_Anphax
from Simple_Anpha34     import Simple_GLKA as Simple_Anphax34
from Simple_CBAM        import Simple_GLKA as Simple_CBAM
from Simple_GLKAconv1x1 import Simple_GLKA as Simple_GLKAconv1x1

PYTORCH_REGISTRY = {
    "CNN"        : (Simple_CNN,         "CNN"),
    "Anpha+"     : (Simple_AnphaPlus,   "Anpha+"),
    "Anphax"     : (Simple_Anphax,      "Anphax"),
    "Anphax34"   : (Simple_Anphax34,    "Anphax34"),
    "CBAM"       : (Simple_CBAM,        "CBAM"),
    "GLKAconv1x1": (Simple_GLKAconv1x1, "GLKAconv1x1"),
}

ONNX_REGISTRY = {
    "CNN"        : "CNN.onnx",
    "Anpha+"     : "Anpha+.onnx",
    "Anphax"     : "Anphax.onnx",
    "Anphax34"   : "Anphax34.onnx",
    "CBAM"       : "CBAM.onnx",
    "GLKAconv1x1": "GLKAconv1x1.onnx",
}

YOLO_REGISTRY = {
    "YOLO_traffic": r"C:\Users\ThisPC\Documents\GitHub\Traffic_Control\Benchmark\traffic_cls\weights\best.pt",
}

NUM_CLASSES = 2

# =========================================================
# HELPERS
# =========================================================
def _stats(times):
    lo_pct = 5 if PLATFORM in ("pi4", "pi5") else 2
    hi_pct = 95 if PLATFORM in ("pi4", "pi5") else 98
    lo, hi = np.percentile(times, lo_pct), np.percentile(times, hi_pct)
    t = times[(times >= lo) & (times <= hi)]
    return {
        "mean"  : float(np.mean(t)),
        "median": float(np.median(t)),
        "std"   : float(np.std(t)),
        "p95"   : float(np.percentile(t, 95)),
        "p99"   : float(np.percentile(t, 99)),
    }

def _make_result(label, rtype, run_means, run_medians, run_p95s, extra=None):
    final_mean    = float(np.median(run_means))
    final_median  = float(np.median(run_medians))
    final_p95     = float(np.median(run_p95s))
    final_fps     = float(1000 / final_mean)
    run_stability = float(np.std(run_means))
    print(f"    -> Mean={final_mean:.3f}ms  FPS={final_fps:.1f}  Stability=+-{run_stability:.3f}ms")
    r = {
        "label"        : label,
        "type"         : rtype,
        "device"       : PLATFORM,
        "mean_ms"      : final_mean,
        "median_ms"    : final_median,
        "p95_ms"       : final_p95,
        "fps"          : final_fps,
        "run_stability": run_stability,
    }
    if extra:
        r.update(extra)
    return r

def _run_loop_cpu(fn, warmup, test):
    for _ in range(warmup):
        fn()
    gc.collect()
    times = []
    for _ in range(test):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return np.array(times)

def _run_loop_gpu(fn, warmup, test):
    with torch.no_grad():
        for _ in range(warmup):
            fn()
    torch.cuda.synchronize()
    gc.collect()
    torch.cuda.empty_cache()
    starts = [torch.cuda.Event(enable_timing=True) for _ in range(test)]
    ends   = [torch.cuda.Event(enable_timing=True) for _ in range(test)]
    with torch.no_grad():
        for i in range(test):
            starts[i].record()
            fn()
            ends[i].record()
    torch.cuda.synchronize()
    return np.array([starts[i].elapsed_time(ends[i]) for i in range(test)])

# =========================================================
# BENCHMARK PYTORCH
# =========================================================
def benchmark_pytorch(label, model_class, folder):
    weight_path = os.path.join(project_root, "runs_cnn", folder, "best_acc.pth")
    if not os.path.exists(weight_path):
        return None

    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    try:
        model = model_class(num_classes=NUM_CLASSES).to(DEVICE).eval()
        model.load_state_dict(torch.load(weight_path, map_location=DEVICE, weights_only=True))
    except Exception:
        try:
            state_dict = torch.load(weight_path, map_location=DEVICE, weights_only=False)
            model.load_state_dict(state_dict, strict=False)
            model.eval()
        except Exception as e:
            print(f"[ERR] PyTorch {label}: {e}")
            return None

    if PLATFORM in ("pi4", "pi5"):
        torch.set_num_threads(4)

    dummy   = torch.randn(1, 3, *SIZE, device=DEVICE)
    run_fn  = (lambda: model(dummy))

    print(f"\n  [PyTorch] {label:<12} ({N_RUNS} runs x {TEST} iters)...")

    run_means, run_medians, run_p95s = [], [], []
    for run_idx in range(N_RUNS):
        times = _run_loop_gpu(run_fn, WARMUP, TEST) if DEVICE == "cuda" else _run_loop_cpu(run_fn, WARMUP, TEST)
        s = _stats(times)
        run_means.append(s["mean"]); run_medians.append(s["median"]); run_p95s.append(s["p95"])
        print(f"    Run {run_idx+1}: Mean={s['mean']:.3f}ms  Median={s['median']:.3f}ms  Std={s['std']:.3f}ms  P95={s['p95']:.3f}ms")
        if run_idx < N_RUNS - 1:
            if DEVICE == "cuda":
                torch.cuda.synchronize(); torch.cuda.empty_cache()
            time.sleep(SLEEP)

    return _make_result(label, "pytorch", run_means, run_medians, run_p95s)

# =========================================================
# BENCHMARK ONNX
# =========================================================
def benchmark_onnx(label, onnx_filename):
    if not ort:
        return None
    onnx_path = os.path.join(ONNX_DIR, onnx_filename)
    if not os.path.exists(onnx_path):
        return None

    gc.collect()
    try:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if PLATFORM == "gpu" else ["CPUExecutionProvider"]
        session  = ort.InferenceSession(onnx_path, providers=providers, sess_options=ort.SessionOptions())
        actual_provider = session.get_providers()[0] if session.get_providers() else "Unknown"
    except Exception as e:
        print(f"[ERR] ONNX {label}: {e}")
        return None

    input_name  = session.get_inputs()[0].name
    dummy_input = np.random.randn(1, 3, 224, 224).astype(np.float32)
    run_fn      = (lambda: session.run(None, {input_name: dummy_input}))

    print(f"\n  [ONNX  ] {label:<12} ({N_RUNS} runs x {TEST} iters) [{actual_provider}]...")

    run_means, run_medians, run_p95s = [], [], []
    for run_idx in range(N_RUNS):
        times = _run_loop_cpu(run_fn, WARMUP, TEST)
        s = _stats(times)
        run_means.append(s["mean"]); run_medians.append(s["median"]); run_p95s.append(s["p95"])
        print(f"    Run {run_idx+1}: Mean={s['mean']:.3f}ms  Median={s['median']:.3f}ms  Std={s['std']:.3f}ms  P95={s['p95']:.3f}ms")
        if run_idx < N_RUNS - 1:
            time.sleep(SLEEP)

    return _make_result(label, "onnx", run_means, run_medians, run_p95s, {"provider": actual_provider})

# =========================================================
# BENCHMARK YOLO (fair — 3 sub-benchmarks)
# =========================================================
def benchmark_yolo(label, weight_path):
    try:
        from ultralytics import YOLO
        from ultralytics.data.augment import LetterBox
    except ImportError:
        print("[ERR] ultralytics not installed")
        return []

    if not os.path.exists(weight_path):
        print(f"[ERR] YOLO weight not found: {weight_path}")
        return []

    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    try:
        yolo  = YOLO(weight_path)
        model = yolo.model.to(DEVICE).eval()
    except Exception as e:
        print(f"[ERR] YOLO {label}: {e}")
        return []

    raw_img   = np.random.randint(0, 255, (*SIZE, 3), dtype=np.uint8)
    letterbox = LetterBox(SIZE)
    lb_img    = letterbox(image=raw_img)
    tensor    = torch.from_numpy(
        lb_img.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    ).to(DEVICE)

    results = []

    # ── 1. FULL predict() ────────────────────────────────────
    print(f"\n  [YOLO  ] {label} [1/3] full predict()  ({N_RUNS} runs x {TEST} iters)...")
    yolo_full = YOLO(weight_path)
    yolo_full.to(DEVICE)

    run_fn_full = (lambda: yolo_full.predict(raw_img, verbose=False, device=DEVICE))
    for _ in range(WARMUP):
        run_fn_full()
    gc.collect()

    run_means, run_medians, run_p95s = [], [], []
    for run_idx in range(N_RUNS):
        times = _run_loop_cpu(run_fn_full, 0, TEST)
        s = _stats(times)
        run_means.append(s["mean"]); run_medians.append(s["median"]); run_p95s.append(s["p95"])
        print(f"    Run {run_idx+1}: Mean={s['mean']:.3f}ms  P95={s['p95']:.3f}ms")
        if run_idx < N_RUNS - 1:
            time.sleep(SLEEP)

    results.append(_make_result(f"{label}_full", "yolo_full", run_means, run_medians, run_p95s))

    # ── 2. PURE INFERENCE (model.forward, CUDA events) ───────
    print(f"\n  [YOLO  ] {label} [2/3] pure inference  ({N_RUNS} runs x {TEST} iters)...")

    infer_fn = (lambda: model(tensor))

    run_means, run_medians, run_p95s = [], [], []
    for run_idx in range(N_RUNS):
        times = _run_loop_gpu(infer_fn, WARMUP, TEST) if DEVICE == "cuda" else _run_loop_cpu(infer_fn, WARMUP, TEST)
        s = _stats(times)
        run_means.append(s["mean"]); run_medians.append(s["median"]); run_p95s.append(s["p95"])
        print(f"    Run {run_idx+1}: Mean={s['mean']:.3f}ms  P95={s['p95']:.3f}ms")
        if run_idx < N_RUNS - 1:
            if DEVICE == "cuda":
                torch.cuda.synchronize(); torch.cuda.empty_cache()
            time.sleep(SLEEP)

    results.append(_make_result(f"{label}_infer", "yolo_infer", run_means, run_medians, run_p95s))

    # ── 3. PREPROCESS ONLY (CPU, no model) ───────────────────
    print(f"\n  [YOLO  ] {label} [3/3] preprocess only ({N_RUNS * TEST} iters)...")
    gc.collect()

    pre_fn = (lambda: torch.from_numpy(
        letterbox(image=raw_img).transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    ).to(DEVICE))

    times = _run_loop_cpu(pre_fn, WARMUP, TEST * N_RUNS)
    s     = _stats(times)
    fm    = s["mean"]
    print(f"    -> Mean={fm:.3f}ms  P95={s['p95']:.3f}ms")

    results.append({
        "label"        : f"{label}_pre",
        "type"         : "yolo_pre",
        "device"       : PLATFORM,
        "mean_ms"      : fm,
        "median_ms"    : s["median"],
        "p95_ms"       : s["p95"],
        "fps"          : float(1000 / fm),
        "run_stability": s["std"],
    })

    return results

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    result = subprocess.run(
        "echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor",
        shell=True, capture_output=True, text=True
    )
    print(result.stdout)

    all_results = []

    print(f"\n{'🔥'*20} PyTorch Benchmark {'🔥'*20}\n")
    for label, (model_class, folder) in PYTORCH_REGISTRY.items():
        r = benchmark_pytorch(label, model_class, folder)
        if r:
            all_results.append(r)

    if ort:
        print(f"\n{'⚡'*20} ONNX Benchmark {'⚡'*20}\n")
        for label, onnx_file in ONNX_REGISTRY.items():
            r = benchmark_onnx(label, onnx_file)
            if r:
                all_results.append(r)

    print(f"\n{'🚀'*20} YOLO Benchmark (fair) {'🚀'*20}\n")
    for label, weight_path in YOLO_REGISTRY.items():
        rs = benchmark_yolo(label, weight_path)
        all_results.extend(rs)

    if not all_results:
        print("❌ No results.")
        sys.exit(0)

    # ─────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────
    print(f"\n{'='*90}")
    print(f"SUMMARY")
    print(f"{'='*90}")
    print(f"{'Model':<22}{'Type':<14}{'Mean(ms)':<12}{'FPS':<10}{'P95(ms)':<12}{'+-Stability'}")
    print("-"*90)

    # CNN models
    for label in PYTORCH_REGISTRY.keys():
        pt_r   = next((r for r in all_results if r["label"] == label and r["type"] == "pytorch"), None)
        onnx_r = next((r for r in all_results if r["label"] == label and r["type"] == "onnx"),    None)
        if pt_r:
            print(f"{pt_r['label']:<22}{'PyTorch':<14}{pt_r['mean_ms']:<12.3f}{pt_r['fps']:<10.1f}{pt_r['p95_ms']:<12.3f}+-{pt_r['run_stability']:.3f}ms")
        if onnx_r:
            speedup = pt_r['mean_ms'] / onnx_r['mean_ms'] if pt_r else 1.0
            print(f"{onnx_r['label']:<22}{'ONNX':<14}{onnx_r['mean_ms']:<12.3f}{onnx_r['fps']:<10.1f}{onnx_r['p95_ms']:<12.3f}+-{onnx_r['run_stability']:.3f}ms  ({speedup:.2f}x)")
        print()

    # YOLO sub-benchmarks
    yolo_types = [("yolo_full", "YOLO full"), ("yolo_infer", "YOLO infer"), ("yolo_pre", "YOLO pre")]
    for rtype, rlabel in yolo_types:
        for r in [x for x in all_results if x["type"] == rtype]:
            print(f"{r['label']:<22}{rlabel:<14}{r['mean_ms']:<12.3f}{r['fps']:<10.1f}{r['p95_ms']:<12.3f}+-{r['run_stability']:.3f}ms")
    print()

    # ─────────────────────────────────────────────────
    # Save
    # ─────────────────────────────────────────────────
    existing_results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            try:
                existing_results = json.load(f)
            except Exception:
                pass

    existing_results.append({
        "timestamp" : time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform"  : PLATFORM,
        "device"    : PLATFORM,
        "warmup"    : WARMUP,
        "test_iters": TEST,
        "n_runs"    : N_RUNS,
        "results"   : all_results,
    })

    with open(RESULT_FILE, "w") as f:
        json.dump(existing_results, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved -> {RESULT_FILE}\n")