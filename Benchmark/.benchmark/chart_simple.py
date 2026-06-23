"""
CNN Benchmark Visualization — Bar Chart (tách pytorch / onnx)
Output: benchmark_pytorch.png, benchmark_onnx.png
"""

import json, os, sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": True,
    "axes.spines.bottom": True,
    "axes.linewidth": 0.8,
    "axes.edgecolor": "#CCCCCC",
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.alpha": 0.15,
    "grid.linewidth": 0.6,
    "grid.color": "#DDDDDD",
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.facecolor": "#FFFFFF",
    "savefig.pad_inches": 0.3,
})

RESULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "cnn_benchmark_results.json")

MODEL_ORDER = ["CNN", "Anphax34", "GLKAconv1x1", "Anpha+", "CBAM", "Anphax"]

PLATFORM_REMAP = {
    "cpu": "pi5",
    "cuda": "gpu",
    "gpu": "gpu",
    "pi5": "pi5",
    "pi4": "pi4",
}

DEVICE_STYLE = {
    "gpu":  dict(label="RTX (GPU)",      color="#0066CC"),
    "pi5":  dict(label="Raspberry Pi 5", color="#00AA55"),
    "pi4":  dict(label="Raspberry Pi 4", color="#FF9900"),
}
DEVICE_ORDER = ["gpu", "pi5", "pi4"]

# ── Load ─────────────────────────────────────────────────────
try:
    with open(RESULT_FILE) as f:
        sessions = json.load(f)
except FileNotFoundError:
    print(f"File not found: {RESULT_FILE}")
    sys.exit(1)

for s in sessions:
    device   = s.get("device", "")
    platform = s.get("platform", "")
    if device in ("pi4", "pi5", "gpu"):
        s["platform"] = device
    else:
        raw = platform or device or "cpu"
        s["platform"] = PLATFORM_REMAP.get(raw, raw)

latest = {}
for s in sessions:
    latest[s["platform"]] = s

print(f"[INFO] Platforms found: {list(latest.keys())}")

# ── Helper ───────────────────────────────────────────────────
def get_vals(platform, run_type, metric):
    if platform not in latest:
        return None
    by_label = {r["label"]: r for r in latest[platform]["results"]
                if r.get("type") == run_type}
    if not by_label:
        return None
    vals = [by_label.get(m, {}).get(metric) for m in MODEL_ORDER]
    if all(v is None for v in vals):
        return None
    return np.array([v if v is not None else np.nan for v in vals], dtype=float)

def platform_has_type(platform, run_type):
    if platform not in latest:
        return False
    return any(r.get("type") == run_type for r in latest[platform]["results"])

# ── Draw figure ───────────────────────────────────────────────
def draw_figure(run_type, title_tag, out_file):
    plats_available = [p for p in DEVICE_ORDER
                       if p in latest and platform_has_type(p, run_type)]
    if not plats_available:
        print(f"[SKIP] Không có data cho run_type='{run_type}'")
        return

    n_models  = len(MODEL_ORDER)
    n_plats   = len(plats_available)
    bar_w     = 0.22
    group_gap = 0.05
    total_w   = n_plats * bar_w + group_gap
    x_center  = np.arange(n_models) * (total_w + 0.25)

    fig = plt.figure(figsize=(16, 7))
    fig.patch.set_facecolor("#FAFAFA")
    fig.text(0.5, 0.98,
             f"CNN Benchmark — {title_tag}",
             ha="center", va="top", fontsize=20, fontweight="bold", color="#1A1A1A")
    fig.text(0.5, 0.955,
             "RTX GPU  •  Raspberry Pi 5  •  Raspberry Pi 4",
             ha="center", va="top", fontsize=11, color="#666666", style="italic")

    gs = GridSpec(1, 2, figure=fig, wspace=0.30,
                  left=0.07, right=0.97, top=0.89, bottom=0.18)
    ax_fps = fig.add_subplot(gs[0, 0])
    ax_lat = fig.add_subplot(gs[0, 1])

    def draw_bars(ax, metric, ylabel, title, annotfmt="{:.1f}"):
        ax.set_facecolor("white")
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12, color="#1A1A1A")
        ax.set_ylabel(ylabel, fontsize=11, fontweight="bold", color="#333333")

        all_y = []
        offsets = np.linspace(-(n_plats - 1) / 2, (n_plats - 1) / 2, n_plats) * bar_w

        for i, plat in enumerate(plats_available):
            st = DEVICE_STYLE[plat]
            y  = get_vals(plat, run_type, metric)
            if y is None:
                continue
            xpos = x_center + offsets[i]
            bars = ax.bar(xpos, np.nan_to_num(y), width=bar_w * 0.88,
                          color=st["color"], alpha=0.85,
                          label=st["label"], zorder=3,
                          edgecolor="white", linewidth=0.5)
            for xi, yi in zip(xpos, y):
                if not np.isnan(yi):
                    ax.annotate(annotfmt.format(yi),
                                xy=(xi, yi), xytext=(0, 4),
                                textcoords="offset points",
                                ha="center", fontsize=7.5,
                                color=st["color"], fontweight="bold")
            all_y.extend(y[~np.isnan(y)].tolist())

        ax.set_xticks(x_center)
        ax.set_xticklabels(MODEL_ORDER, fontsize=10, fontweight="bold",
                           rotation=20, ha="right")
        ax.grid(axis="y", alpha=0.2)

        if len(all_y) >= 2:
            mn, mx = min(all_y), max(all_y)
            if mx / (mn + 1e-9) > 20:
                ax.set_yscale("log")
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(
                    lambda v, _: f"{v:.0f}" if v >= 10 else f"{v:.1f}"
                ))

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, frameon=True, fontsize=8.5, loc="best",
                      edgecolor="#CCCCCC", fancybox=True, framealpha=0.92)

    draw_bars(ax_fps, "fps",     "FPS",          "FPS  (Higher = Better)",    annotfmt="{:.1f}")
    draw_bars(ax_lat, "mean_ms", "Latency (ms)", "Latency  (Lower = Better)", annotfmt="{:.0f}ms")

    plats_found = [p for p in DEVICE_ORDER if p in latest]
    fig.text(0.5, 0.01,
             f"Platforms: {', '.join(plats_found)}  •  {len(sessions)} session(s)  •  {title_tag}",
             ha="center", fontsize=9, color="#999999")

    plt.savefig(out_file, facecolor="#FAFAFA", edgecolor="none")
    print(f"Saved → {out_file}")
    plt.close()

# ── Export 2 file ─────────────────────────────────────────────
base = os.path.dirname(os.path.abspath(__file__))
draw_figure("pytorch", "PyTorch", os.path.join(base, "benchmark_pytorch.png"))
draw_figure("onnx",    "ONNX",    os.path.join(base, "benchmark_onnx.png"))