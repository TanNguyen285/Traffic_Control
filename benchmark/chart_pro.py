import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import os

# ==========================================================
# CẤU HÌNH GIAO DIỆN PREMIUM
# ==========================================================
COLORS = ['#00a8ff', '#fbc531', '#4cd137', '#e84118', '#9c88ff', '#487eb0', '#00d2d3', '#54a0ff', '#5f27cd']

def draw_benchmark_bar_chart():
    print("\n--- TOOL VẼ BIỂU ĐỒ CỘT HIỆU NĂNG ---")
    path = input("Nhập đường dẫn file JSON dữ liệu: ").strip().replace('"', '').replace("'", "")
    
    if not os.path.exists(path):
        print(f"❌ Không tìm thấy file tại: {path}")
        return

    # 1. Đọc dữ liệu
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Lỗi đọc file: {e}")
        return

    # Trích xuất thông tin
    labels = [item['label'] for item in data]
    fps_values = [item['fps'] for item in data]
    latency_values = [item['mean_ms'] for item in data]
    x = np.arange(len(labels))

    # 2. Khởi tạo biểu đồ 2 tầng (FPS và Latency)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), dpi=150)
    fig.patch.set_facecolor('#f8f9fa')

    def add_labels(ax, values, unit=""):
        """Hàm ghi số liệu trên đầu cột"""
        for i, v in enumerate(values):
            ax.text(i, v + (v * 0.02), f'{v:.1f}{unit}', 
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color='#2d3436')

    # --- TẦNG 1: BIỂU ĐỒ FPS ---
    bars1 = ax1.bar(x, fps_values, color=COLORS[:len(labels)], edgecolor='black', linewidth=0.5, alpha=0.85)
    ax1.set_title('SO SÁNH TỐC ĐỘ XỬ LÝ (FPS)', fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Frames Per Second (FPS)', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=15, ha='right')
    ax1.grid(axis='y', linestyle='--', alpha=0.3)
    add_labels(ax1, fps_values)
    
    # Dùng thang đo log nếu chênh lệch quá lớn (như SCI 1500 vs YOLO 41)
    # ax1.set_yscale('log') # Bỏ comment nếu muốn dùng log scale cho FPS

    # --- TẦNG 2: BIỂU ĐỒ LATENCY ---
    bars2 = ax2.bar(x, latency_values, color=COLORS[:len(labels)], edgecolor='black', linewidth=0.5, alpha=0.85)
    ax2.set_title('SO SÁNH ĐỘ TRỄ TRUNG BÌNH (LATENCY)', fontsize=16, fontweight='bold', pad=20)
    ax2.set_ylabel('Time (ms)', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=15, ha='right')
    ax2.grid(axis='y', linestyle='--', alpha=0.3)
    add_labels(ax2, latency_values, "ms")

    # Tự động điều chỉnh khoảng cách để không đè chữ
    plt.tight_layout(pad=4.0)
    
    output_name = "benchmark_bar_report.png"
    plt.savefig(output_name, dpi=300, bbox_inches='tight')
    
    print(f"\n--- HOÀN THÀNH ---")
    print(f"📊 Biểu đồ cột đã lưu tại: {os.path.abspath(output_name)}")

if __name__ == "__main__":
    draw_benchmark_bar_chart()