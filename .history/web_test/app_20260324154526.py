import os
import sys

# --- XỬ LÝ ĐƯỜNG DẪN (QUAN TRỌNG) ---
# Lấy đường dẫn thư mục hiện tại (web_test)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Lấy đường dẫn thư mục SCI
SCI_DIR = os.path.join(CURRENT_DIR, "SCI")

# Thêm cả 2 vào hệ thống để các file con tự tìm thấy nhau
sys.path.append(CURRENT_DIR)
sys.path.append(SCI_DIR)

# --- BÂY GIỜ MỚI IMPORT CÁC MODULE KHÁC ---
from flask import Flask, render_template, jsonify, Response, request
import torch
import cv2
import numpy as np
from ultralytics import YOLO
from torchvision import transforms

# Import các class hệ thống
from camera import Camera
from yoloxx import Yolo_AI
from uart_service import UARTService
from web_test.tienxulyanh import Tienxulyanh
from SimpleCNN.custom import SimpleCNN
from logic import TrafficLogic  # File logic bạn vừa tách

app = Flask(__name__)

# ==========================================================
# 2. KHỞI TẠO BIẾN (Chỉ khai báo, không viết logic chạy ở đây)
# ==========================================================
class Config:
    YOLO_PATH = "runs/detect/yolov26_epoch50/weights/best_ncnn_model"
    CNN_PATH = "runs/exp3/best_cnn_model.pth"
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    CNN_CLASSES = ["Thong Thoang", "Ket Xe"]
    YOLO_CLASSES = ['car', 'van', 'bus', 'motorcycle', 'truck']

# Khởi tạo phần cứng & AI
cam = Camera(src=0)
cam.start()

uart = UARTService(port="COM3") # Hoặc ttyAMA0 tùy máy
pre_proc = Tienxulyanh(target_size=(640, 640))

# Load Models
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

# KHỞI TẠO ENGINE (Toàn bộ logic nằm trong này)
engine = TrafficLogic(ai_yolo, cnn_net, cnn_transform, Config.CNN_CLASSES, Config.DEVICE, pre_proc, uart, cam)

selected_image = None

# ==========================================================
# 3. ROUTES (Định tuyến giao diện)
# ==========================================================
@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    global selected_image
    # Gọi engine xử lý, app.py không cần biết bên trong làm gì
    res, _ = engine.perform_detection(selected_image)
    selected_image = None 
    return jsonify(res)

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

# Cleanup khi tắt app
import atexit
atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)