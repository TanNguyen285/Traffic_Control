import os
import sys
# ==========================================================
# 1. XỬ LÝ HỆ THỐNG & ĐƯỜNG DẪN
# ==========================================================
# Lấy đường dẫn tuyệt đối của thư mục chứa file app.py hiện tại
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Đưa các thư mục này vào danh sách tìm kiếm của Python để có thể import các file nội bộ
sys.path.append(CURRENT_DIR)
# ==========================================================
# 2. IMPORT CÁC THƯ VIỆN CẦN THIẾT
# ==========================================================
from flask import Flask, render_template, jsonify, Response, request
import torch
import cv2
import numpy as np
from ultralytics import YOLO
from torchvision import transforms

# --- Import các Class chức năng ---
from camera import Camera           # Quản lý lấy luồng hình ảnh từ Webcam
from yolov26 import Yolo_AI          # Wrapper xử lý logic nhận diện đối tượng YOLO
from uart_service import UART_config # Dịch vụ gửi/nhận dữ liệu qua cổng Serial (RS232/TTL)
from tienxulyanh import Tienxulyanh  # Các hàm chuẩn hóa kích thước/màu sắc ảnh
from SimpleCNN.custom import SimpleCNN # Cấu trúc mạng Neural phân loại kẹt xe
from logic_2 import TrafficLogic      # "Bộ não" điều phối toàn bộ luồng xử lý AI
from cnn import Simple_CNN_config   # Wrapper xử lý logic dự đoán trạng thái từ CNN
from ethernet import EthernetService # Dịch vụ giao tiếp giữa 2 trạm qua Ethernet (TCP/IP)
app = Flask(__name__)

# ==========================================================
# 3. CẤU HÌNH HỆ THỐNG (CONFIG)
# ==========================================================
class Config:
    # Đường dẫn tới file model YOLO đã được tối ưu (định dạng NCNN cho CPU)
    YOLO_PATH = "runs/detect/yolov26_epoch50/weights/best_ncnn_model"
    # Đường dẫn tới file model CNN phân loại trạng thái
    CNN_PATH = "runs/exp3/best_cnn_model.pth"
    # Đường dẫn tới file model SCI
    SCI_PATH = "web_test/weights/difficult.pt"
    # Tự động chọn GPU (cuda) nếu có, nếu không dùng CPU
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Tên các nhãn phân loại của mô hình CNN
    CNN_CLASSES = ["Thong Thoang", "Ket Xe"]
    # Các loại phương tiện mà mô hình YOLO sẽ tập trung nhận diện
    YOLO_CLASSES = ['car', 'van', 'bus', 'motorcycle', 'truck']

# ==========================================================
# 4. KHỞI TẠO PHẦN CỨNG & MÔ HÌNH AI
# ==========================================================
# Khởi tạo Camera và bắt đầu luồng đọc hình ảnh ngầm
cam = Camera(src=0)
cam.start()
# Khởi tạo UART Service và bắt đầu lắng nghe lệnh từ ESP32
uart = UART_config(port="/dev/ttyAMA0", baudrate=115200)
uart.start_listening(trigger_callback=lambda: print("[UART] Lệnh 'yell' nhận được từ ESP32"))

# Khởi tạo dịch vụ Ethernet để giao tiếp giữa 2 trạm (A và B)
eth_service = EthernetService(station_id='A', peer_ip='192.168.1.100')  # Thay thế bằng địa chỉ IP thực tế của trạm B

# Khởi tạo bộ tiền xử lý ảnh (Resize về 640x640 cho YOLO)
pre_proc = Tienxulyanh(sci_path=Config.SCI_PATH, target_size=(640, 640), use_sci=True)

# --- Tải mô hình YOLO ---
yolo_model = YOLO(Config.YOLO_PATH)
ai_yolo = Yolo_AI(yolo_model, class_names=Config.YOLO_CLASSES)

# --- Tải mô hình CNN ---
cnn_net = SimpleCNN(num_classes=2).to(Config.DEVICE)
cnn_net.load_state_dict(torch.load(Config.CNN_PATH, map_location=Config.DEVICE))
cnn_net.eval() # Chuyển sang chế độ dự đoán (không phải huấn luyện)

# --- Cấu hình chuẩn hóa ảnh cho CNN (giống hệt lúc huấn luyện) ---
cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])
# --- Khởi tạo Service CNN ---
# Gom nhóm model, transform và config vào một chỗ để dễ quản lý
cnn_service = Simple_CNN_config(
    model=cnn_net, 
    transform=cnn_transform, 
    classes=Config.CNN_CLASSES, 
    device=Config.DEVICE
)

# --- Khởi tạo ENGINE điều phối (TrafficLogic mới) ---
# Bây giờ engine chỉ nhận cnn_service thay vì nhận lẻ tẻ từng biến cnn_net, cnn_transform
engine = TrafficLogic(
    yolo_ai=ai_yolo, 
    cnn_service=cnn_service, 
    pre_proc=pre_proc, 
    uart=uart, 
    cam=cam,
    eth_service=eth_service, # Truyền đối tượng EthernetService vào engine để sử dụng trong logic
    station_id='A', # Xác định đây là trạm A hay B (ảnh hưởng đến logic phân xử)
)

# Biến tạm lưu trữ ảnh người dùng tải lên từ giao diện web
selected_image = None

# ==========================================================
# 5. CÁC ROUTE (ĐƯỜNG DẪN WEB)
# ==========================================================

@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    global selected_image
    res, _ = engine.perform_detection(selected_image)
    selected_image = None # Reset lại ảnh sau khi xử lý xong
    return jsonify(res) # Trả kết quả JSON về cho giao diện Web

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global selected_image
    file = request.files.get('file')
    if file:
        nparr = np.frombuffer(file.read(), np.uint8)
        selected_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return jsonify({"success": True})
    return jsonify({"error": "No file"}), 400

@app.route('/camera_stream')
def camera_stream():
    def gen():
        while True:
            ret, frame = cam.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ==========================================================
# 6. QUẢN LÝ ĐÓNG HỆ THỐNG
# ==========================================================
import atexit
# Đảm bảo khi tắt server Flask, camera sẽ được tắt đúng cách để không bị treo port
atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    # Chạy server ở port 8000, host 0.0.0.0 để các máy trong mạng LAN có thể truy cập
    app.run(host="0.0.0.0", port=8000, debug=False)