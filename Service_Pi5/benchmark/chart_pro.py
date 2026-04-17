import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import json
import os
from adjustText import adjust_text

# ==========================================================
# CẤU HÌNH GIAO DIỆN PREMIUM
# ==========================================================
COLORS = ['#00a8ff', '#fbc531', '#4cd137', '#e84118', '#9c88ff', '#487eb0']
MARKERS = ['o', 's', '^', 'D', 'v', 'p']

def draw_comparison_line_chart():
    print("\n--- TOOL SO SÁNH HIỆU NĂNG (BẢN FIX ĐÈ CHỮ TUYỆT ĐỐI) ---")
    paths_input = input("Nhập các đường dẫn file JSON (cách nhau bởi dấu phẩy): ").strip()
    
    # Làm sạch đường dẫn
    paths = [p.strip().replace('"', '').replace("'", "") for p in paths_input.split(',')]
    
    all_data = {}
    master_models = set()

    # 1. Đọc dữ liệu từ các file
    for path in paths:
        if not os.path.exists(path):
            print(f"⚠️ Bỏ qua: Không tìm thấy file {path}")
            continue
        
        device_name = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_data[device_name] = data
                master_models.update(data.keys())
        except Exception as e:
            print(f"❌ Lỗi khi xử lý file {device_name}: {e}")

    if not all_data:
        print("❌ Không có dữ liệu hợp lệ để vẽ biểu đồ!")
        return

    # Sắp xếp danh sách Model cố định trên trục X
    sorted_models = sorted(list(master_models))
    x_indexes = np.arange(len(sorted_models))

    # 2. Khởi tạo biểu đồ
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12), dpi=150)
    fig.patch.set_facecolor('#fdfdfd') # Màu nền tổng thể hơi xám nhẹ cho chuyên nghiệp

    # --- TRONG HÀM plot_metric, ÔNG CẬP NHẬT CÁC DÒNG SAU ---

    def plot_metric(ax, metric_key, title, is_latency=False):
        texts = [] 
        ax.set_facecolor('white')
        
        # 1. Dùng thang đo Logarit để các thiết bị yếu không bị dính chùm vào nhau
        ax.set_yscale('symlog', linthresh=10) # symlog giúp hiển thị tốt cả số nhỏ gần 0

        for i, (device, models) in enumerate(all_data.items()):
            values = [models.get(m, {}).get(metric_key, None) for m in sorted_models]
            
            line, = ax.plot(x_indexes, values, label=device, 
                            color=COLORS[i % len(COLORS)], 
                            marker=MARKERS[i % len(MARKERS)], 
                            linewidth=3, markersize=8, alpha=0.9)

            for idx, val in enumerate(values):
                if val is not None:
                    # Tăng khoảng cách theo thiết bị để số không chồng lên nhau
                    # Thiết bị i=0 số nằm trên, i=1 số nằm dưới, i=2 nằm trên nữa...
                    direction = 1 if i % 2 == 0 else -1
                    
                    label_text = f'{val:.1f}' + ('ms' if is_latency else '')
                    t = ax.text(idx, val, label_text, 
                                fontsize=9, 
                                fontweight='bold', 
                                color=line.get_color(),
                                ha='center',
                                bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=0))
                    texts.append(t)

        # 2. Cấu hình lại adjust_text cực mạnh
        adjust_text(texts, 
                    ax=ax, 
                    expand_points=(3, 3), 
                    expand_text=(2, 2),
                    only_move={'points':'y', 'text':'y'},
                    force_points=2.0,
                    force_text=2.5,
                    arrowprops=dict(arrowstyle='-', color='gray', lw=0.5, alpha=0.3))

        # 3. Định dạng lại trục Y để nhìn số không bị lạ (biến log thành số thường)
        from matplotlib.ticker import ScalarFormatter
        ax.yaxis.set_major_formatter(ScalarFormatter())
        
        ax.set_title(title, fontweight='bold', fontsize=16, pad=25)
        ax.set_xticks(x_indexes)
        ax.set_xticklabels(sorted_models, rotation=15, ha='right')
        ax.grid(True, which="both", linestyle=':', alpha=0.4) # Grid cả vạch phụ
        ax.legend(loc='upper right')
        ax.margins(y=0.3)

    # 3. Tiến hành vẽ 2 tầng: FPS và Latency
    plot_metric(ax1, 'fps', 'SO SÁNH TỐC ĐỘ XỬ LÝ (FPS)')
    plot_metric(ax2, 'latency_ms', 'SO SÁNH ĐỘ TRỄ (LATENCY)', is_latency=True)

    # 4. Lưu kết quả
    plt.tight_layout(pad=5.0)
    output_name = "benchmark_final_report.png"
    plt.savefig(output_name, dpi=300, bbox_inches='tight')
    
    print(f"\n--- HOÀN THÀNH ---")
    print(f"📊 Ảnh báo cáo đẹp đã được lưu tại: {os.path.abspath(output_name)}")

if __name__ == "__main__":
    draw_comparison_line_chart(),