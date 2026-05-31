"""
Unified CNN Benchmark - PyTorch + ONNX
So sanh performance giua .pth vs .onnx tren GPU / Pi4 / Pi5
"""

import torch
import numpy as np
import time
import os, sys, json, gc, platform
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
    """Tra ve 'gpu' | 'pi4' | 'pi5' | 'cpu'"""
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

# Params toi uu
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

ONNX_DIR     = os.path.join(project_root, "onnx_models")
RESULT_FILE  = os.path.join(current_dir, "cnn_benchmark_results.json")

print("=" * 75)
print(f"🔬 UNIFIED CNN BENCHMARK - PyTorch + ONNX")
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

NUM_CLASSES = 2

# =========================================================
# PYTORCH BENCHMARK
# =========================================================
def _pytorch_single_run(model, dummy):
    use_cuda = (DEVICE == "cuda")
    
    with torch.no_grad():
        for _ in range(WARMUP):
            model(dummy)
    if use_cuda:
        torch.cuda.synchronize()
    
    gc.collect()
    if use_cuda:
        torch.cuda.empty_cache()
    
    times = []
    with torch.no_grad():
        if use_cuda:
            starts = [torch.cuda.Event(enable_timing=True) for _ in range(TEST)]
            ends   = [torch.cuda.Event(enable_timing=True) for _ in range(TEST)]
            for i in range(TEST):
                starts[i].record()
                model(dummy)
                ends[i].record()
            torch.cuda.synchronize()
            times = [starts[i].elapsed_time(ends[i]) for i in range(TEST)]
        else:
            for _ in range(TEST):
                t0 = time.perf_counter()
                model(dummy)
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1000)
    
    return np.array(times)

# =========================================================
# ONNX BENCHMARK
# =========================================================
def _onnx_single_run(session, dummy_input):
    input_name = session.get_inputs()[0].name
    
    for _ in range(WARMUP):
        session.run(None, {input_name: dummy_input})
    
    gc.collect()
    
    times = []
    for _ in range(TEST):
        t0 = time.perf_counter()
        session.run(None, {input_name: dummy_input})
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    
    return np.array(times)

# =========================================================
# STATS
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
        model.load_state_dict(
            torch.load(weight_path, map_location=DEVICE, weights_only=True)
        )
    except Exception as e:
        # Try with strict=False and weights_only=False
        try:
            state_dict = torch.load(weight_path, map_location=DEVICE, weights_only=False)
            model.load_state_dict(state_dict, strict=False)
            model.eval()
        except Exception as e2:
            print(f"[ERR] PyTorch {label}: {e2}")
            return None

    if PLATFORM in ("pi4", "pi5"):
        torch.set_num_threads(4)

    dummy = torch.randn(1, 3, *SIZE, device=DEVICE)

    print(f"\n  [PyTorch] {label:<12} ({N_RUNS} runs x {TEST} iters)...")

    run_means, run_medians, run_p95s, run_stds = [], [], [], []

    for run_idx in range(N_RUNS):
        times = _pytorch_single_run(model, dummy)
        s     = _stats(times)

        run_means.append(s["mean"])
        run_medians.append(s["median"])
        run_p95s.append(s["p95"])
        run_stds.append(s["std"])

        print(f"    Run {run_idx+1}: Mean={s['mean']:.3f}ms  Median={s['median']:.3f}ms  Std={s['std']:.3f}ms  P95={s['p95']:.3f}ms")

        if run_idx < N_RUNS - 1:
            if DEVICE == "cuda":
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
            time.sleep(SLEEP)

    final_mean    = float(np.median(run_means))
    final_median  = float(np.median(run_medians))
    final_p95     = float(np.median(run_p95s))
    final_fps     = float(1000 / final_mean)
    run_stability = float(np.std(run_means))

    print(f"    -> Mean={final_mean:.3f}ms  FPS={final_fps:.1f}  Stability=+-{run_stability:.3f}ms")

    return {
        "label"        : label,
        "type"         : "pytorch",
        "device"       : PLATFORM,
        "mean_ms"      : final_mean,
        "median_ms"    : final_median,
        "p95_ms"       : final_p95,
        "fps"          : final_fps,
        "run_stability": run_stability,
    }

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
        session = ort.InferenceSession(
            onnx_path,
            providers=providers,
            sess_options=ort.SessionOptions()
        )
        actual_provider = session.get_providers()[0] if session.get_providers() else "Unknown"
    except Exception as e:
        print(f"[ERR] ONNX {label}: Failed to load - {e}")
        return None

    dummy_input = np.random.randn(1, 3, 224, 224).astype(np.float32)

    print(f"\n  [ONNX  ] {label:<12} ({N_RUNS} runs x {TEST} iters) [{actual_provider}]...")

    run_means, run_medians, run_p95s, run_stds = [], [], [], []

    for run_idx in range(N_RUNS):
        times = _onnx_single_run(session, dummy_input)
        s     = _stats(times)

        run_means.append(s["mean"])
        run_medians.append(s["median"])
        run_p95s.append(s["p95"])
        run_stds.append(s["std"])

        print(f"    Run {run_idx+1}: Mean={s['mean']:.3f}ms  Median={s['median']:.3f}ms  Std={s['std']:.3f}ms  P95={s['p95']:.3f}ms")

        if run_idx < N_RUNS - 1:
            time.sleep(SLEEP)

    final_mean    = float(np.median(run_means))
    final_median  = float(np.median(run_medians))
    final_p95     = float(np.median(run_p95s))
    final_fps     = float(1000 / final_mean)
    run_stability = float(np.std(run_means))

    print(f"    -> Mean={final_mean:.3f}ms  FPS={final_fps:.1f}  Stability=+-{run_stability:.3f}ms")

    return {
        "label"        : label,
        "type"         : "onnx",
        "device"       : PLATFORM,
        "provider"     : actual_provider,
        "mean_ms"      : final_mean,
        "median_ms"    : final_median,
        "p95_ms"       : final_p95,
        "fps"          : final_fps,
        "run_stability": run_stability,
    }

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

    if not all_results:
        print("❌ No results.")
        sys.exit(0)

    # ─────────────────────────────────────────────────
    # Summary by Model
    # ─────────────────────────────────────────────────
    print(f"\n{'='*85}")
    print(f"COMPARISON: PyTorch vs ONNX")
    print(f"{'='*85}")
    print(f"{'Model':<14}{'Type':<10}{'Mean(ms)':<12}{'FPS':<10}{'P95(ms)':<12}{'+-Stability':<15}")
    print("-"*85)

    for label in PYTORCH_REGISTRY.keys():
        pytorch_res = next((r for r in all_results if r["label"] == label and r["type"] == "pytorch"), None)
        onnx_res = next((r for r in all_results if r["label"] == label and r["type"] == "onnx"), None)

        if pytorch_res:
            print(f"{pytorch_res['label']:<14}{'PyTorch':<10}"
                  f"{pytorch_res['mean_ms']:<12.3f}"
                  f"{pytorch_res['fps']:<10.1f}"
                  f"{pytorch_res['p95_ms']:<12.3f}"
                  f"+-{pytorch_res['run_stability']:.3f}ms")

        if onnx_res:
            speedup = pytorch_res['fps'] / onnx_res['fps'] if pytorch_res else 1.0
            print(f"{onnx_res['label']:<14}{'ONNX':<10}"
                  f"{onnx_res['mean_ms']:<12.3f}"
                  f"{onnx_res['fps']:<10.1f}"
                  f"{onnx_res['p95_ms']:<12.3f}"
                  f"+-{onnx_res['run_stability']:.3f}ms  ({speedup:.2f}x)")
        print()

    # ─────────────────────────────────────────────────
    # Save results
    # ─────────────────────────────────────────────────
    existing_results = []
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE) as f:
            try:
                existing_results = json.load(f)
            except Exception:
                pass

    existing_results.append({
        "timestamp"  : time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform"   : PLATFORM,
        "device"     : PLATFORM,
        "warmup"     : WARMUP,
        "test_iters" : TEST,
        "n_runs"     : N_RUNS,
        "results"    : all_results,
    })

    with open(RESULT_FILE, "w") as f:
        json.dump(existing_results, f, indent=2, ensure_ascii=False)
    #bật 2.4Ghz để ổn định xung chạy AI và giảm độ trễ
    

    print(f"✅ Saved -> {RESULT_FILE}\n")