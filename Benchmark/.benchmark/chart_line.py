import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import os

# ==========================================================
# CẤU HÌNH — thêm thiết bị mới vào đây nếu cần
# ==========================================================
DEVICE_COLORS = [
    '#00a8ff', '#4cd137', '#fbc531', '#e84118', '#9c88ff',
]

MODEL_ORDER = [
    'YOLO_PT', 'YOLO_NCNN',
    'SimpleCNN_PTH', 'SimpleCNN_ONNX',
    'Anpha_PTH', 'Anpha_ONNX',
    'GLKA_PTH', 'GLKA_ONNX',
    'SCI',
]

# ==========================================================
# ĐỌC DỮ LIỆU
# ==========================================================
def load_json(path):
    path = path.strip().strip('"').strip("'")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Không tìm thấy file: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['label']: item for item in data}

def collect_data(devices_data):
    all_labels = []
    for label in MODEL_ORDER:
        for d in devices_data.values():
            if label in d:
                all_labels.append(label)
                break
    # fallback: label có trong data nhưng không có trong MODEL_ORDER
    for dev_data in devices_data.values():
        for label in dev_data:
            if label not in all_labels:
                all_labels.append(label)

    fps_table     = {dev: [] for dev in devices_data}
    latency_table = {dev: [] for dev in devices_data}

    for label in all_labels:
        for dev, d in devices_data.items():
            fps_table[dev].append(d[label]['fps'] if label in d else 0)
            latency_table[dev].append(d[label]['mean_ms'] if label in d else 0)

    return all_labels, fps_table, latency_table

# ==========================================================
# VẼ BIỂU ĐỒ — tự động điều chỉnh theo số thiết bị
# ==========================================================
def plot_chart(ax, labels, table, ylabel, title, unit="", log_scale=False):
    devices   = list(table.keys())
    n_devices = len(devices)
    x         = np.arange(len(labels))

    if n_devices == 1:
        # 1 thiết bị → vẽ line chart
        dev    = devices[0]
        values = table[dev]
        ax.plot(x, values, marker='o', linewidth=2,
                color=DEVICE_COLORS[0], label=dev, zorder=3)
        ax.fill_between(x, values, alpha=0.12, color=DEVICE_COLORS[0])
        for i, v in enumerate(values):
            if v > 0:
                ax.text(i, v + max(values) * 0.02, f'{v:.1f}{unit}',
                        ha='center', va='bottom', fontsize=8,
                        fontweight='bold', color='#2d3436', zorder=4)
    else:
        # 2-3+ thiết bị → grouped bar chart
        # width tự động thu hẹp nếu nhiều thiết bị
        width = min(0.22, 0.7 / n_devices)
        for i, dev in enumerate(devices):
            offset = (i - n_devices / 2 + 0.5) * width
            values = table[dev]
            bars = ax.bar(
                x + offset, values,
                width=width,
                color=DEVICE_COLORS[i % len(DEVICE_COLORS)],
                edgecolor='white', linewidth=0.6,
                alpha=0.88, label=dev, zorder=3,
            )
            for bar, v in zip(bars, values):
                if v > 0:
                    y_offset = bar.get_height() * (1.05 if log_scale else 1.02)
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + (0 if log_scale else bar.get_height() * 0.01),
                        f'{v:.1f}{unit}',
                        ha='center', va='bottom',
                        fontsize=7.5, fontweight='bold', color='#2d3436', zorder=4,
                    )

    ax.set_title(title, fontsize=13, fontweight='bold', pad=14)
    ax.set_ylabel(ylabel, fontweight='bold', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=9)
    ax.grid(axis='y', linestyle='--', alpha=0.35, zorder=0)
    ax.set_facecolor('#f8f9fa')
    if log_scale:
        ax.set_yscale('log')
    ax.legend(fontsize=9, loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

# ==========================================================
# MAIN
# ==========================================================
def main():
    print("=== BENCHMARK COMPARE ===")
    print("Nhập đường dẫn từng file JSON (Enter để kết thúc, tối thiểu 1 file):\n")

    devices_data = {}
    idx = 1
    while True:
        path = input(f"  File JSON #{idx} (hoặc Enter để bỏ qua): ").strip()
        if not path:
            if idx == 1:
                print("  ✗ Cần ít nhất 1 file.")
                continue
            break
        try:
            data = load_json(path)
            # Lấy tên thiết bị từ tên file nếu không có key 'device' chung
            device_name = os.path.splitext(os.path.basename(path))[0]
            # Nếu tất cả item cùng device thì dùng luôn
            devs = list({v.get('device', '') for v in data.values()})
            if len(devs) == 1 and devs[0]:
                device_name = devs[0]
            devices_data[device_name] = data
            print(f"  ✓ [{device_name}] — {len(data)} model")
            idx += 1
        except Exception as e:
            print(f"  ✗ Lỗi: {e}")

    n = len(devices_data)
    chart_type = "line" if n == 1 else "grouped bar"
    print(f"\n→ {n} thiết bị — vẽ dạng {chart_type}\n")

    labels, fps_table, latency_table = collect_data(devices_data)
    title_suffix = f"({n} thiết bị)" if n > 1 else f"({list(devices_data.keys())[0]})"

    # ---------- ẢNH 1: FPS ----------
    fig1, ax1 = plt.subplots(figsize=(14, 6), dpi=150)
    fig1.patch.set_facecolor('#ffffff')
    plot_chart(ax1, labels, fps_table,
               ylabel='Frames Per Second (FPS)',
               title=f'So sánh tốc độ xử lý (FPS) — {title_suffix}')
    plt.tight_layout(pad=3.0)
    fig1.savefig('benchmark_fps.png', dpi=200, bbox_inches='tight')
    print(f"✓ Đã lưu: {os.path.abspath('benchmark_fps.png')}")

    # ---------- ẢNH 2: LATENCY ----------
    fig2, ax2 = plt.subplots(figsize=(14, 6), dpi=150)
    fig2.patch.set_facecolor('#ffffff')
    plot_chart(ax2, labels, latency_table,
               ylabel='Độ trễ trung bình (ms)',
               title=f'So sánh độ trễ trung bình (ms) — {title_suffix}',
               unit='ms')
    plt.tight_layout(pad=3.0)
    fig2.savefig('benchmark_latency.png', dpi=200, bbox_inches='tight')
    print(f"✓ Đã lưu: {os.path.abspath('benchmark_latency.png')}")

    print("\n=== XONG ===")

if __name__ == "__main__":
    main()