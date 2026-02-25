import time
import numpy as np
from ultralytics import YOLO
import psutil # Để đo tải CPU

# --- CẤU HÌNH ---
MODEL_PATH = 'runs/detect/yolov26_trained/weights/best_ncnn_model' # Thay đổi ở đây
DATA_YAML = 'data.yaml'
IMG_SIZE = 640
WARMUP_ITER = 10   # Chạy mồi để CPU ổn định xung nhịp
TEST_ITER = 100    # Chạy 100 lần để lấy giá trị trung bình (chuẩn khoa học)

def benchmark_pi5():
    print(f"--- Đang khởi tạo mô hình: {MODEL_PATH} ---")
    
    try:
        # 1. Load Model
        model = YOLO(MODEL_PATH)
        
        # 2. Warm-up (Cực kỳ quan trọng trên Pi 5 để tránh số liệu ảo lúc đầu)
        print(f"Đang Warm-up {WARMUP_ITER} lần...")
        for _ in range(WARMUP_ITER):
            model.predict(source="https://ultralytics.com/images/bus.jpg", imgsz=IMG_SIZE, device='cpu', verbose=False)

        # 3. Chạy đo chính thức
        print(f"Đang đo chính thức {TEST_ITER} lần...")
        inference_times = []
        
        for i in range(TEST_ITER):
            start = time.perf_counter() # Dùng perf_counter để độ chính xác cực cao
            results = model.predict(source="https://ultralytics.com/images/bus.jpg", imgsz=IMG_SIZE, device='cpu', verbose=False)
            end = time.perf_counter()
            
            # Tính thời gian inference thuần túy từ kết quả của Ultralytics
            # (Hoặc dùng end - start nếu muốn tính cả thời gian xử lý ảnh đầu vào)
            inf_time = results[0].speed['inference']
            inference_times.append(inf_time)
            
            if (i+1) % 20 == 0:
                print(f"Đã xong {i+1}/{TEST_ITER} lần...")

        # 4. Tính toán số liệu thống kê
        avg_time = np.mean(inference_times)
        std_time = np.std(inference_times) # Độ lệch chuẩn (để xem tốc độ có ổn định không)
        max_time = np.max(inference_times)
        min_time = np.min(inference_times)
        fps = 1000 / avg_time

        # 5. Xuất bảng số liệu "Pro"
        print("\n" + "="*50)
        print(f"KẾT QUẢ BENCHMARK TRÊN RASPBERRY PI 5")
        print(f"Mô hình: {MODEL_PATH}")
        print("-" * 50)
        print(f"Số lần chạy: {TEST_ITER}")
        print(f"Thời gian Inference TB: {avg_time:.2f} ms")
        print(f"Độ lệch chuẩn (Std):    {std_time:.2f} ms")
        print(f"Nhanh nhất:            {min_time:.2f} ms")
        print(f"Chậm nhất:             {max_time:.2f} ms")
        print(f"Tốc độ khung hình (FPS): {fps:.2f}")
        print(f"Tải CPU hiện tại:      {psutil.cpu_percent()}%")
        print("="*50)

    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    benchmark_pi5()