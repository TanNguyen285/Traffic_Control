import matplotlib
matplotlib.use('Agg')  # Đảm bảo chạy mượt trên cả Rasp và Laptop
import matplotlib.pyplot as plt
import numpy as np
import json
import os
import matplotlib.ticker as ticker

# ==========================================================
# CẤU HÌNH MÀU SẮC (XANH - CAM)
# ==========================================================
COLOR_LATENCY = '#3498db'  # Xanh Blue (Ocean)
COLOR_FPS = '#e67e22'      # Cam Vibrant (Orange)
FONT_SIZE_TITLE = 18
FONT_SIZE_LABEL = 12

def draw_benchmark_blue_orange(json_path):
    # 1. Đọc dữ liệu JSON
    if not os.path.exists(json_path):
        print(f"Lỗi: Không tìm thấy file JSON tại {json_path}")
        return
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Lỗi khi đọc file: {e}")
        return

    # 2. Xử lý và Sắp xếp (Theo Latency tăng dần để tạo hình bậc thang)
    sorted_items = sorted(data.items(), key=lambda x: x[1]['latency_ms'])
    labels = [item[0] for item in sorted_items]
    latency = [item[1]['latency_ms'] for item in sorted_items]
    fps = [item[1]['fps'] for item in sorted_items]

    # 3. Thiết lập Layout
    x = np.arange(len(labels))  
    width = 0.38  # Độ rộng tối ưu cho cột đôi
    fig, ax = plt.subplots(figsize=(14, 8), dpi=100)
    
    # Lưới ngang mờ để dễ dóng hàng
    ax.grid(axis='y', linestyle='--', alpha=0.3, color='gray', zorder=0)
    
    # Loại bỏ viền thừa (Spines) cho phong cách hiện đại
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')

    # 4. Vẽ cột Xanh - Cam
    rects1 = ax.bar(x - width/2, latency, width, label='Latency (ms)', 
                    color=COLOR_LATENCY, edgecolor='none', alpha=0.9, zorder=3)
    
    rects2 = ax.bar(x + width/2, fps, width, label='FPS (Tốc độ)', 
                    color=COLOR_FPS, edgecolor='none', alpha=0.9, zorder=3)

    # 5. Cài đặt nhãn và tiêu đề
    ax.set_ylabel('Giá trị đo lường', fontsize=FONT_SIZE_LABEL, fontweight='bold')
    ax.set_title('HIỆU NĂNG TRÊN RASPBERRY PI 5 (2GB) \n(Phân tích Latency vs FPS)', 
                 fontsize=FONT_SIZE_TITLE, fontweight='bold', pad=30)
    
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha='right', fontsize=10)
    
    # Legend (Chú thích)
    ax.legend(frameon=True, shadow=False, facecolor='white', loc='upper right')

    # 6. Ghi số liệu lên đỉnh cột (Ghi đúng màu để dễ nhận diện)
    def autolabel(rects, color_text):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 6), 
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9.5, fontweight='bold', color=color_text)

    autolabel(rects1, '#2980b9') # Xanh đậm hơn một chút để dễ đọc số
    autolabel(rects2, '#d35400') # Cam đậm hơn một chút để dễ đọc số

    # 7. Xuất file
    fig.tight_layout()
    output_name = "benchmark_laptop.png"
    plt.savefig(output_name, dpi=300, bbox_inches='tight')
    
    print(f"\n--- HOÀN THÀNH ---")
    print(f"Biểu đồ Xanh-Cam đã được lưu: {os.path.abspath(output_name)}")

if __name__ == "__main__":
    path = input("Nhập đường dẫn file JSON: ").strip()
    path = path.replace('"', '').replace("'", "")
    draw_benchmark_blue_orange(path)