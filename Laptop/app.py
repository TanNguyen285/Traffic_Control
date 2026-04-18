import os
import sys
import threading
import cv2
import numpy as np
import torch
import atexit
import webview
import time
from flask import Flask, render_template, jsonify, Response, request
from ultralytics import YOLO
from torchvision import transforms

# ================= 1. PATH & MODULE SETUP =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from camera import Camera
    from yoloxx import Yolo_AI
    from tienxulyanh import Tienxulyanh
    from SimpleCNN.custom import SimpleCNN
    from logic import TrafficLogic
    print("✅ Local modules imported successfully.")
except ImportError as e:
    print(f"❌ Import Error: {e}")

app = Flask(__name__)

# ================= 2. CONFIGURATION =================
class Config:
    YOLO_PATH = os.path.join(BASE_DIR, "runs", "detect", "yolov26_epoch50", "weights", "best_ncnn_model")
    CNN_PATH  = os.path.join(BASE_DIR, "runs", "exp3", "best_cnn_model.pth")
    SCI_PATH  = os.path.join(BASE_DIR, "weights", "medium.pt")
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    CNN_CLASSES = ["Thong Thoang", "Ket Xe"]
    YOLO_CLASSES = ['car', 'van', 'bus', 'motorcycle', 'truck']

# ================= 3. INITIALIZATION =================

# Khởi tạo Camera A (Laptop)
try:
    cam_a = Camera(src=0)
    cam_a.start()
    print("✅ Camera A (Laptop) initialized.")
except Exception as e:
    print(f"❌ Camera A Error: {e}")
    cam_a = None

# Khởi tạo Camera B (USB)
try:
    cam_b = Camera(src=1) # Thử 1 hoặc 2 nếu không nhận
    cam_b.start()
    print("✅ Camera B (USB) initialized.")
except Exception as e:
    print(f"❌ Camera B Error: {e}")
    cam_b = None

# UART Dummy
class DummyUART:
    def send(self, data): pass
    def close(self): pass
uart = DummyUART()

# Load Models
pre_proc = Tienxulyanh(target_size=(640, 640), sci_model_path=Config.SCI_PATH)

ai_yolo = None
try:
    yolo_net = YOLO(Config.YOLO_PATH) 
    yolo_net.predict(np.zeros((640, 640, 3), dtype=np.uint8), imgsz=640, verbose=False)
    ai_yolo = Yolo_AI(yolo_net, class_names=Config.YOLO_CLASSES)
    print(f"✅ YOLO (NCNN) loaded.")
except Exception as e:
    print(f"❌ YOLO Load Error: {e}")

cnn_net = None
try:
    cnn_net = SimpleCNN(num_classes=2).to(Config.DEVICE)
    weights = torch.load(Config.CNN_PATH, map_location=Config.DEVICE)
    cnn_net.load_state_dict(weights)
    cnn_net.eval()
    print(f"✅ CNN loaded.")
except Exception as e:
    print(f"❌ CNN Load Error: {e}")

cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Engine xử lý chung
engine = TrafficLogic(
    ai_yolo, cnn_net, cnn_transform,
    Config.CNN_CLASSES, Config.DEVICE,
    pre_proc, uart, None # cam được truyền trực tiếp trong route
)

# ================= 4. UTILS =================

def process_frame(frame):
    """Hàm bổ trợ để xử lý AI và chuẩn hóa kết quả"""
    try:
        result, cmd = engine.perform_detection(frame)
        if isinstance(result, dict):
            counts = result.get('counts', [0] * 5)
            if isinstance(counts, dict):
                result['counts'] = [counts.get(c, 0) for c in Config.YOLO_CLASSES]
        result['timestamp'] = int(time.time() * 1000)
        return result
    except Exception as e:
        return {'error': str(e), 'timestamp': 0}

def gen_frames(camera_obj):
    """Hàm generator cho stream video"""
    while True:
        if camera_obj is None: break
        ret, frame = camera_obj.read()
        if not ret or frame is None:
            time.sleep(0.04)
            continue
        _, jpeg = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

# ================= 5. FLASK ROUTES =================

@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

@app.route('/detect_static', methods=['POST'])
def detect_static():
    file = request.files.get('image') or request.files.get('file')
    if not file: return jsonify({'error': 'Không gửi ảnh'}), 400
    nparr = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None: return jsonify({'error': 'Ảnh không hợp lệ'}), 400
    return jsonify(process_frame(img))

@app.route('/data_a')
def data_a():
    if cam_a is None: return jsonify({'error': 'Camera A offline'})
    ret, frame = cam_a.read()
    if not ret: return jsonify({'error': 'No frame A'})
    return jsonify(process_frame(frame))

@app.route('/data_b')
def data_b():
    if cam_b is None: return jsonify({'error': 'Camera B offline'})
    ret, frame = cam_b.read()
    if not ret: return jsonify({'error': 'No frame B'})
    return jsonify(process_frame(frame))

@app.route('/camera_stream_1')
def camera_stream_1():
    return Response(gen_frames(cam_a), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera_stream_2')
def camera_stream_2():
    return Response(gen_frames(cam_b), mimetype='multipart/x-mixed-replace; boundary=frame')

# ================= 6. CLEANUP & EXIT =================

def cleanup():
    if cam_a: cam_a.stop()
    if cam_b: cam_b.stop()
    print("🧹 Cleanup complete. All cameras stopped.")

atexit.register(cleanup)

def start_flask():
    app.run(host="127.0.0.1", port=8000, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    time.sleep(2)
    webview.create_window("Hệ thống Giao thông AI - 2 Camera", "http://127.0.0.1:8000", width=1280, height=720)
    webview.start()
    os._exit(0)