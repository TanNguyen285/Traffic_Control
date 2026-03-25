import os
import sys
import threading
import cv2
import numpy as np
import torch
import atexit
import webview
import time
import base64
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

# 1. Camera
try:
    cam = Camera(src=0)
    cam.start()
    print("✅ Camera initialized.")
except Exception as e:
    print(f"❌ Camera Error: {e}")
    cam = None

# 2. UART Dummy
class DummyUART:
    def send(self, data): pass
    def close(self): pass
uart = DummyUART()

# 3. Load Models
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

engine = TrafficLogic(
    ai_yolo, cnn_net, cnn_transform,
    Config.CNN_CLASSES, Config.DEVICE,
    pre_proc, uart, cam
)

# ================= 4. FLASK ROUTES =================

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

    try:
        # SỬA LỖI LỆCH BIẾN: logic.py trả về (result, cmd)
        # result ĐÃ CHỨA SẴN 'processed_image' (Base64) bên trong
        result, cmd = engine.perform_detection(img)
        
        # Cập nhật timestamp thật mới để JS giữ lại kết quả này
        result['timestamp'] = int(time.time() * 1000)
        
        return jsonify(result)
    except Exception as exc:
        print(f"❌ Lỗi detect_static: {exc}")
        return jsonify({'error': str(exc)}), 500

@app.route('/data_a')
def data_a():
    if cam is None:
        return jsonify({'error': 'Camera offline', 'timestamp': 0})

    ret, frame = cam.read()
    if not ret or frame is None:
        return jsonify({'error': 'Không frame', 'timestamp': 0})

    try:
        # Tương tự như trên: hứng result và cmd
        result, cmd = engine.perform_detection(frame)
        
        # Chuẩn hóa counts thành List để JS dễ đọc
        if isinstance(result, dict):
            counts = result.get('counts', [0] * 5)
            if isinstance(counts, dict):
                result['counts'] = [counts.get(c, 0) for c in Config.YOLO_CLASSES]
        
        result['timestamp'] = int(time.time() * 1000)
        return jsonify(result)
    except Exception as exc:
        return jsonify({'error': str(exc), 'timestamp': 0})

@app.route('/data_b')
def data_b():
    return jsonify({
        'counts': [0] * 5,
        'total_vehicles': 0,
        'green_seconds': 0,
        'yellow_seconds': 0,
        'red_seconds': 60,
        'timestamp': int(time.time() * 1000)
    })

@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            if cam is None: break
            ret, frame = cam.read()
            if not ret or frame is None:
                time.sleep(0.04)
                continue
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Thêm alias cho các stream nếu JS gọi tên khác
@app.route('/camera_stream_1')
def camera_stream_1(): return video_feed()

@app.route('/camera_stream_2')
def camera_stream_2():
    blank = np.zeros((480, 480, 3), dtype=np.uint8)
    _, jpeg = cv2.imencode('.jpg', blank)
    return Response(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n', mimetype='multipart/x-mixed-replace; boundary=frame')

# ================= 5. CLEANUP & EXIT =================

def cleanup():
    if cam: cam.stop()
    print("🧹 Cleanup complete.")

atexit.register(cleanup)

def start_flask():
    app.run(host="127.0.0.1", port=8000, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    time.sleep(2)
    webview.create_window("Hệ thống Giao thông AI", "http://127.0.0.1:8000", width=1280, height=720)
    webview.start()
    os._exit(0)