from flask import Flask, render_template, jsonify, Response, request
from ultralytics import YOLO
import torch
import os, atexit, platform, cv2
import numpy as np
from torchvision import transforms

# Import các thành phần của bạn
from camera import Camera
from yoloxx import Yolo_AI
from uart_service import UARTService
from pre_processor_image import Tienxulyanh
from model.custom import SimpleCNN
from logic import TrafficLogic # Import logic vừa táchfrom flask import Flask, render_template, jsonify, Response, request
from ultralytics import YOLO
import torch
import os, atexit, platform, cv2
import numpy as np
from torchvision import transforms

# Import các thành phần của bạn
from camera import Camera
from yoloxx import Yolo_AI
from uart_service import UARTService
from pre_processor_image import Tienxulyanh
from model.custom import SimpleCNN
from logic import TrafficLogic # Import logic vừa tách

app = Flask(__name__)

# --- KHỞI TẠO BIẾN (CONFIGURATION) ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
YOLO_PATH = "runs/detect/yolov26_epoch50/weights/best_ncnn_model"
CNN_PATH = "runs/exp3/best_cnn_model.pth"
CNN_CLASSES = ["Thong Thoang", "Ket Xe"]

# --- KHỞI TẠO ĐỐI TƯỢNG ---
cam = Camera(src=0)
cam.start()

uart = UARTService(port="/dev/ttyAMA0" if platform.system() == "Linux" else "COM3")
pre_proc = Tienxulyanh(target_size=(640, 640))

# Load Models
yolo_model = YOLO(YOLO_PATH)
ai_yolo = Yolo_AI(yolo_model, class_names=['car', 'van', 'bus', 'motorcycle', 'truck'])

cnn_net = SimpleCNN(num_classes=2).to(DEVICE)
cnn_net.load_state_dict(torch.load(CNN_PATH, map_location=DEVICE))
cnn_net.eval()

cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# KHỞI TẠO ENGINE TRUNG TÂM
traffic_engine = TrafficLogic(ai_yolo, cnn_net, cnn_transform, CNN_CLASSES, DEVICE, pre_proc, uart, cam)

selected_image = None

# --- ROUTES ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    global selected_image
    res, _ = traffic_engine.perform_detection(selected_image)
    selected_image = None # Reset sau khi xử lý
    return jsonify(res)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global selected_image
    file = request.files['file']
    nparr = np.frombuffer(file.read(), np.uint8)
    selected_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return jsonify({"success": True})

@app.route('/camera_stream')
def camera_stream():
    def gen():
        while True:
            ret, frame = cam.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# UART Trigger
uart.start_listening(lambda: traffic_engine.perform_detection())

atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

app = Flask(__name__)

# --- KHỞI TẠO BIẾN (CONFIGURATION) ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
YOLO_PATH = "runs/detect/yolov26_epoch50/weights/best_ncnn_model"
CNN_PATH = "runs/exp3/best_cnn_model.pth"
CNN_CLASSES = ["Thong Thoang", "Ket Xe"]

# --- KHỞI TẠO ĐỐI TƯỢNG ---
cam = Camera(src=0)
cam.start()

uart = UARTService(port="/dev/ttyAMA0" if platform.system() == "Linux" else "COM3")
pre_proc = Tienxulyanh(target_size=(640, 640))

# Load Models
yolo_model = YOLO(YOLO_PATH)
ai_yolo = Yolo_AI(yolo_model, class_names=['car', 'van', 'bus', 'motorcycle', 'truck'])

cnn_net = SimpleCNN(num_classes=2).to(DEVICE)
cnn_net.load_state_dict(torch.load(CNN_PATH, map_location=DEVICE))
cnn_net.eval()

cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# KHỞI TẠO ENGINE TRUNG TÂM
traffic_engine = TrafficLogic(ai_yolo, cnn_net, cnn_transform, CNN_CLASSES, DEVICE, pre_proc, uart, cam)

selected_image = None

# --- ROUTES ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    global selected_image
    res, _ = traffic_engine.perform_detection(selected_image)
    selected_image = None # Reset sau khi xử lý
    return jsonify(res)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global selected_image
    file = request.files['file']
    nparr = np.frombuffer(file.read(), np.uint8)
    selected_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return jsonify({"success": True})

@app.route('/camera_stream')
def camera_stream():
    def gen():
        while True:
            ret, frame = cam.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# UART Trigger
uart.start_listening(lambda: traffic_engine.perform_detection())

atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)