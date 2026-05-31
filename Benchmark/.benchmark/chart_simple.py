"""
CNN Benchmark Visualization — Line Chart
Output: benchmark_report.png
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
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "benchmark_report.png")

MODEL_ORDER = ["CNN", "Anphax34", "GLKAconv1x1", "Anpha+", "CBAM", "Anphax"]

# ── Map tên platform cũ → chuẩn ─────────────────────────────
PLATFORM_REMAP = {
    "cpu": "pi5",   # đang chạy trên Pi5
    "cuda": "gpu",
    "gpu": "gpu",
    "pi5": "pi5",
    "pi4": "pi4",
}

DEVICE_STYLE = {
    "gpu": dict(label="RTX (GPU)",       color="#0066CC", marker="o", markersize=8, linewidth=2.5, zorder=4),
    "pi5": dict(label="Raspberry Pi 5",  color="#00AA55", marker="s", markersize=8, linewidth=2.5, zorder=3),
    "pi4": dict(label="Raspberry Pi 4",  color="#FF9900", marker="^", markersize=8, linewidth=2.5, zorder=2),
}
DEVICE_ORDER = ["gpu", "pi5", "pi4"]

# ── Load ─────────────────────────────────────────────────────
try:
    with open(RESULT_FILE) as f:
        sessions = json.load(f)
except FileNotFoundError:
    print(f"File not found: {RESULT_FILE}")
    sys.exit(1)

# Chuẩn hóa platform
for s in sessions:
    raw = s.get("platform") or s.get("device", "cpu")
    s["platform"] = PLATFORM_REMAP.get(raw, raw)

# Lấy session mới nhất mỗi platform
latest = {}
for s in sessions:
    latest[s["platform"]] = s

print(f"[INFO] Platforms found: {list(latest.keys())}")
for plat, sess in latest.items():
    types = set(r.get("type") for r in sess["results"])
    print(f"  {plat}: {len(sess['results'])} results, types={types}")

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

def platform_has_onnx(platform):
    if platform not in latest:
        return False
    return any(r.get("type") == "onnx" for r in latest[platform]["results"])

# ── Figure ───────────────────────────────────────────────────
x = np.arange(len(MODEL_ORDER))

fig = plt.figure(figsize=(16, 7))
fig.patch.set_facecolor("#FAFAFA")
fig.text(0.5, 0.98, "CNN Benchmark Report",
         ha="center", va="top", fontsize=20, fontweight="bold", color="#1A1A1A")
fig.text(0.5, 0.955,
         "RTX GPU  •  Raspberry Pi 5  •  Raspberry Pi 4   |   liền = PyTorch    đứt = ONNX",
         ha="center", va="top", fontsize=11, color="#666666", style="italic")

gs = GridSpec(1, 2, figure=fig, wspace=0.30,
              left=0.07, right=0.97, top=0.89, bottom=0.18)
ax_fps = fig.add_subplot(gs[0, 0])
ax_lat = fig.add_subplot(gs[0, 1])

def draw_lines(ax, metric, ylabel, title, annotfmt="{:.1f}"):
    ax.set_facecolor("white")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12, color="#1A1A1A")
    ax.set_ylabel(ylabel, fontsize=11, fontweight="bold", color="#333333")
    ax.set_xticks(x)
    ax.set_xticklabels(MODEL_ORDER, fontsize=10, fontweight="bold",
                       rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.2)

    all_y = []

    for plat in DEVICE_ORDER:
        if plat not in latest:
            continue
        st = DEVICE_STYLE[plat]

        # PyTorch — đường liền
        y_pt = get_vals(plat, "pytorch", metric)
        if y_pt is not None:
            ax.plot(x, y_pt,
                    color=st["color"], marker=st["marker"],
                    linestyle="-", linewidth=st["linewidth"],
                    markersize=st["markersize"], alpha=1.0,
                    label=st["label"], zorder=st["zorder"])
            for xi, yi in zip(x, y_pt):
                if not np.isnan(yi):
                    ax.annotate(annotfmt.format(yi),
                                xy=(xi, yi), xytext=(0, 7),
                                textcoords="offset points",
                                ha="center", fontsize=7.5,
                                color=st["color"], fontweight="bold")
            all_y.extend(y_pt[~np.isnan(y_pt)].tolist())

        # ONNX — đường đứt
        if platform_has_onnx(plat):
            y_onnx = get_vals(plat, "onnx", metric)
            if y_onnx is not None:
                ax.plot(x, y_onnx,
                        color=st["color"], marker=st["marker"],
                        linestyle="--", linewidth=st["linewidth"] - 0.5,
                        markersize=st["markersize"] - 2, alpha=0.55,
                        label=st["label"] + " (ONNX)", zorder=st["zorder"])
                for xi, yi in zip(x, y_onnx):
                    if not np.isnan(yi):
                        ax.annotate(annotfmt.format(yi),
                                    xy=(xi, yi), xytext=(0, -13),
                                    textcoords="offset points",
                                    ha="center", fontsize=7.5,
                                    color=st["color"], alpha=0.7)
                all_y.extend(y_onnx[~np.isnan(y_onnx)].tolist())

    # Log scale chỉ khi có data và range đủ rộng
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

draw_lines(ax_fps, "fps",     "FPS",          "FPS  (Higher = Better)",    annotfmt="{:.1f}")
draw_lines(ax_lat, "mean_ms", "Latency (ms)", "Latency  (Lower = Better)", annotfmt="{:.0f}ms")

plats_found = [p for p in DEVICE_ORDER if p in latest]
fig.text(0.5, 0.01,
         f"Platforms: {', '.join(plats_found)}  •  {len(sessions)} session(s)",
         ha="center", fontsize=9, color="#999999")

plt.savefig(OUT_FILE, facecolor="#FAFAFA", edgecolor="none")
print(f"Saved → {OUT_FILE}")
plt.close()