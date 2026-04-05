import os
import sys
import queue
import json
import torch
import cv2
import numpy as np
import atexit
from flask import Flask, render_template, jsonify, Response, request
from ultralytics import YOLO
from torchvision import transforms

# --- Import các Class nội bộ ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from camera import Camera 
from yolov26 import Yolo_AI 
from uart_service import UART_config 
from tienxulyanh import Tienxulyanh 
from SimpleCNN.custom import SimpleCNN 
from logic_2 import TrafficLogic 
from cnn import Simple_CNN_config 
from ethernet import EthernetService 

app = Flask(__name__)

# HÀNG ĐỢI (QUEUE): Mấu chốt để Web tự nhảy ảnh khi có biến đổi
web_update_queue = queue.Queue()

class Config:
    YOLO_PATH = "runs/detect/yolov26_epoch50/weights/best_ncnn_model"
    CNN_PATH = "runs/exp3/best_cnn_model.pth"
    SCI_PATH = "web_test/weights/difficult.pt"
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    CNN_CLASSES = ["Thong Thoang", "Ket Xe"]
    YOLO_CLASSES = ['car', 'van', 'bus', 'motorcycle', 'truck']

# --- KHỞI TẠO HỆ THỐNG ---
cam = Camera(src=0)
cam.start()

# UART config (Để trống port nếu test trên PC không có hardware)
uart = UART_config(port="COM1", baudrate=115200) 
eth_service = EthernetService(station_id='Tram_A', peer_ip='192.168.1.100')
pre_proc = Tienxulyanh(sci_path=Config.SCI_PATH, target_size=(640, 640), use_sci=True)

yolo_model = YOLO(Config.YOLO_PATH)
ai_yolo = Yolo_AI(yolo_model, class_names=Config.YOLO_CLASSES)

cnn_net = SimpleCNN(num_classes=2).to(Config.DEVICE)
cnn_net.load_state_dict(torch.load(Config.CNN_PATH, map_location=Config.DEVICE))
cnn_net.eval()

cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

cnn_service = Simple_CNN_config(model=cnn_net, transform=cnn_transform, classes=Config.CNN_CLASSES, device=Config.DEVICE)

engine = TrafficLogic(
    yolo_ai=ai_yolo, 
    cnn_service=cnn_service, 
    pre_proc=pre_proc, 
    uart=uart, 
    cam=cam,
    eth_service=eth_service, 
    station_id='Tram_A',
)

# Lắng nghe UART thật (nếu có)
uart.start_listening(engine.uart_esp32_rasp)

selected_image = None

# ==========================================================
# CÁC ROUTE XỬ LÝ
# ==========================================================

@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

# ROUTE QUAN TRỌNG: Dùng để Test Logic mà không cần bấm nút trên Web
@app.route('/test_logic/<cmd>')
def test_logic(cmd):
    """
    Giả lập y hệt như ESP32 gửi lệnh qua UART.
    Cách dùng: Gõ localhost:8000/test_logic/run trên trình duyệt
    """
    global selected_image
    print(f"\n[HARDWARE SIM] Nhận tín hiệu giả lập: {cmd}")
    
    # 1. Kích hoạt biến trong Logic (giống UART gọi)
    engine.uart_esp32_rasp(cmd) 
    
    # 2. Thực thi AI
    res, uart_cmd = engine.thuc_thi_AI(selected_image)
    selected_image = None
    
    if res:
        # 3. Đẩy vào Queue để trang Web chính tự nhảy ảnh
        web_update_queue.put(res)
        return jsonify({
            "tin_hieu_gia_lap": cmd,
            "lenh_tra_ve_uart": uart_cmd,
            "cnn_status": res.get("cnn_status"),
            "xe_dem_duoc": res.get("xe_local")
        })
    return "AI không chạy, kiểm tra biến run!"

@app.route('/update_web')
def update_web():
    """ Trang Web chính sẽ luôn treo ở đây để chờ ảnh mới """
    try:
        data = web_update_queue.get(timeout=20) # Chờ 20s
        return jsonify(data)
    except queue.Empty:
        return jsonify({}), 204

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    global selected_image
    # Khi bấm thủ công trên web, cũng ép biến run lên
    engine.uart_esp32_rasp('run')
    res, _ = engine.thuc_thi_AI(selected_image)
    selected_image = None
    return jsonify(res)

@app.route('/camera_stream')
def camera_stream():
    def gen():
        while True:
            ret, frame = cam.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global selected_image
    file = request.files.get('file')
    if file:
        nparr = np.frombuffer(file.read(), np.uint8)
        selected_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return jsonify({"success": True})
    return jsonify({"error": "No file"}), 400

atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True)