from flask import Flask, render_template, jsonify, request, url_for, Response
from ultralytics import YOLO
import cv2
import os
import uuid
import urllib.request
import numpy as np
import json
import threading
import time
import atexit
try:
    import serial
except ImportError:
    serial = None

# -------------------------------------------------------------------------
# LẤY ĐƯỜNG DẪN THƯ MỤC HIỆN TẠI (BASE DIRECTORY)
# -------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Khởi tạo Flask, chỉ định thư mục chứa template và static
app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)

# Thư mục chứa ảnh upload và ảnh output
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(STATIC_DIR, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------------------------------------------------------
# LOAD MODEL YOLO
# -------------------------------------------------------------------------

# Lấy đường dẫn tuyệt đối của model YOLO
model_path = os.path.join(BASE_DIR, "../../runs/detect/my_yolov8n_train_meme/weights/best.pt")

# Nếu đường dẫn tuyệt đối không tồn tại → dùng đường dẫn tương đối
if not os.path.exists(model_path):
    model_path = "runs/detect/my_yolov8n_train_meme/weights/best.pt"

# Load model YOLO vào RAM (mất thời gian 1 lần duy nhất)
model = YOLO(model_path)

# -------------------------------------------------------------------------
# LOAD DANH SÁCH CLASS TỪ FILE classes.txt
# -------------------------------------------------------------------------
classes_file = os.path.join(BASE_DIR, '..', '..', 'vehicle dataset', 'classes.txt')
if os.path.exists(classes_file):
    try:
        with open(classes_file, 'r', encoding='utf-8') as f:
            CLASS_NAMES = [line.strip() for line in f.readlines() if line.strip()]
    except Exception:
        CLASS_NAMES = []
else:
    CLASS_NAMES = []

@app.route("/")
def index():
    # Trả về giao diện chính + gửi danh sách tên lớp về frontend
    return render_template("index.html", class_names=CLASS_NAMES)

# -------------------------------------------------------------------------
# LỚP CAMERA HANDLER — ĐỌC CAMERA Ở LUỒNG NỀN
# -------------------------------------------------------------------------
# Mục đích:
# - Đọc camera liên tục mà không bị lag
# - Lưu frame cuối cùng để các API khác lấy dùng
# - Hỗ trợ reconnect khi camera bị lỗi
# -------------------------------------------------------------------------
class CameraHandler:
    def __init__(self, src=0, reconnect_interval=2.0, max_missed=20):
        self.src = src
        self.reconnect_interval = reconnect_interval  # thời gian thử kết nối lại camera
        self.max_missed = max_missed  # số frame lỗi tối đa trước khi reset camera
        self.cap = None          # đối tượng VideoCapture
        self.frame = None        # frame mới nhất
        self.lock = threading.Lock()   # tránh xung đột khi đọc / ghi frame
        self.thread = None
        self.running = False
        self._missed = 0         # đếm số frame lỗi liên tiếp
    def _open(self):
        """ Mở kết nối camera. Nếu đang mở thì release rồi mở lại. """
        try:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
            # Windows dùng CAP_DSHOW tránh delay lúc mở camera
            if os.name == 'nt':
                self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(self.src)
            # giảm buffer để hạn chế độ trễ
            try:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
        except Exception:
            self.cap = None
    def start(self):
        """ Bắt đầu đọc camera trong thread riêng """
        if self.running:
            return
        self.running = True
        self._open()  # mở camera lần đầu
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()
    def _reader(self):
        """ Luồng nền: đọc camera theo vòng lặp liên tục """
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self._open()                        # thử mở lại camera
                time.sleep(self.reconnect_interval)
                continue
            try:
                ret, frame = self.cap.read()       # đọc một frame
            except Exception:
                ret, frame = False, None
            if not ret or frame is None:
                self._missed += 1
                if self._missed >= self.max_missed:
                    # Nếu lỗi quá nhiều → reset camera
                    try:
                        self._open()
                    except Exception:
                        pass
                    self._missed = 0
                time.sleep(0.05)
                continue
            # Lưu frame vào biến chung
            with self.lock:
                self.frame = frame.copy()

            self._missed = 0
            time.sleep(0.01)

    def read(self):
        """ Lấy frame mới nhất """
        with self.lock:
            if self.frame is None:
                return False, None
            return True, self.frame.copy()

    def is_opened(self):
        """ Kiểm tra camera có mở được hay không """
        return self.cap is not None and self.cap.isOpened()

    def stop(self):
        """ Tắt thread đọc camera khi app dừng """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass

# Khởi tạo handler và bắt đầu đọc camera
camera_handler = CameraHandler(0)
camera_handler.start()

# Khi app đóng → đảm bảo tắt camera
atexit.register(lambda: camera_handler.stop())

# -------------------------------------------------------------------------
# UART HANDLER - Giao tiếp với ESP32
# -------------------------------------------------------------------------
class UARTHandler:
    def __init__(self, port="/dev/ttyAMA1", baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.uart = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self._connect()
    
    def _connect(self):
        try:
            if serial is None:
                print("serial module not available")
                return
            self.uart = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"UART connected to {self.port}")
        except Exception as e:
            print(f"UART connection failed: {e}")
            self.uart = None
    
    def send(self, msg):
        """Gửi cmd đến ESP32"""
        if self.uart is None:
            return False
        try:
            with self.lock:
                self.uart.write((msg + "\n").encode())
                print(f"UART sent: {msg}")
            return True
        except Exception as e:
            print(f"UART send error: {e}")
            return False
    
    def start_listening(self):
        """Bắt đầu thread lắng nghe UART"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print("UART listener started")
    
    def _listen(self):
        """Thread nền: lắng nghe UART từ ESP32"""
        while self.running:
            if self.uart is None or not self.uart.is_open:
                time.sleep(0.5)
                continue
            try:
                data = self.uart.readline().decode().strip()
                if data:
                    print(f"UART received: {data}")
                    if data.lower() == "yell":
                        # Trigger auto capture & detect
                        self._handle_yell()
            except Exception as e:
                print(f"UART read error: {e}")
                time.sleep(0.1)
    
    def _handle_yell(self):
        """Xử lý khi nhận 'yell' từ ESP32"""
        try:
            # Chụp ảnh + detect
            if not camera_handler.is_opened():
                print("Camera not available")
                return
            
            ret, frame = camera_handler.read()
            if not ret or frame is None:
                print("Failed to capture frame")
                return
            
            if model is None:
                print("Model not loaded")
                return
            
            # Detect
            results = model(frame, conf=0.5, iou=0.5)
            
            # Đếm xe
            num_classes = len(CLASS_NAMES) if CLASS_NAMES else 6
            counts = [0] * num_classes
            try:
                boxes = results[0].boxes
                if hasattr(boxes, 'cls'):
                    cls_vals = boxes.cls
                    try:
                        cls_arr = np.array(cls_vals).astype(int).flatten()
                    except:
                        cls_arr = [int(x) for x in cls_vals]
                    for c in cls_arr:
                        if 0 <= int(c) < num_classes:
                            counts[int(c)] += 1
            except:
                pass
            
            total_vehicles = sum(counts)
            
            # Xác định cmd gửi lại
            if 0 < total_vehicles < 5:
                cmd = "m1"
            elif 5 <= total_vehicles <= 10:
                cmd = "m2"
            elif 10 < total_vehicles <= 20:
                cmd = "m3"
            elif total_vehicles > 20:
                cmd = "m4"
            else:
                cmd = "m0"
            
            # Gửi cmd lại ESP32
            self.send(cmd)
            print(f"Detected {total_vehicles} vehicles, sent {cmd}")
            
        except Exception as e:
            print(f"Error handling yell: {e}")
    
    def stop(self):
        """Tắt UART"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        try:
            if self.uart:
                self.uart.close()
        except:
            pass

uart_handler = UARTHandler()
uart_handler.start_listening()
atexit.register(lambda: uart_handler.stop())

# -------------------------------------------------------------------------
# STREAM CAMERA RA TRÌNH DUYỆT DẠNG MJPEG
# -------------------------------------------------------------------------
def gen_camera_frames():
    """
    Gửi camera live stream dạng MJPEG (ảnh JPEG nối liên tục).
    Trình duyệt <img> tự cập nhật để tạo hiệu ứng video.
    """
    if not camera_handler.is_opened():
        yield b''
        return

    while True:
        ret, frame = camera_handler.read()

        if not ret or frame is None:
            time.sleep(0.05)
            continue

        # encode khung thành JPG
        ret2, jpeg = cv2.imencode('.jpg', frame)
        if not ret2:
            continue

        # MJPEG streaming trả về block JPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

@app.route('/camera_stream')
def camera_stream():
    """
    API hiển thị camera live stream.
    Dùng trong HTML bằng:
        <img src="/camera_stream">
    """
    return Response(gen_camera_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# -------------------------------------------------------------------------
# API CHỤP ẢNH + CHẠY YOLO + TRẢ KẾT QUẢ
# -------------------------------------------------------------------------
@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    """
  t chụp ảnh → lấy frame hiện tại → chạy YOLO → lưu ảnh → trả JSON:
        - URL ảnh detect
        - counts từng class
        - tính thời gian đèn giao thông
    """
    # Kiểm tra camera ok
    if not camera_handler.is_opened():
        return jsonify({"error": "Camera not available"}), 500

    # Lấy frame mới nhất
    ret, frame = camera_handler.read()
    if not ret or frame is None:
        return jsonify({"error": "Không chụp được khung từ camera"}), 500
    # tên file ngẫu nhiên
    timestamp = str(uuid.uuid4())[:8]
    filename = f"camera_{timestamp}.jpg"
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    # lưu ảnh gốc
    cv2.imwrite(save_path, frame)
    # lấy tham số conf, IOU từ frontend
    try:
        conf = float(request.args.get('conf', 0.5))
    except Exception:
        conf = 0.5
    try:
        iou = float(request.args.get('iou', 0.5))
    except Exception:
        iou = 0.5
    # đọc lại ảnh
    img = cv2.imread(save_path)
    if img is None:
        return jsonify({"error": "Không thể đọc ảnh capture"}), 500
    # chạy YOLO detect
    results = model(img, conf=conf, iou=iou)
    # vẽ bbox
    img_out = results[0].plot()
    # lưu ảnh output
    name_only = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    output_filename = f"{name_only}_detect{ext}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    cv2.imwrite(output_path, img_out)
    # đếm số lượng class
    num_classes = len(CLASS_NAMES) if CLASS_NAMES else 6
    counts = [0] * num_classes
    try:
        boxes = results[0].boxes
        if hasattr(boxes, 'cls'):                     # YOLO trả về danh sách cls
            cls_vals = boxes.cls
            try:
                cls_arr = np.array(cls_vals).astype(int).flatten()
            except Exception:
                cls_arr = [int(x) for x in cls_vals]

            for c in cls_arr:
                if 0 <= int(c) < num_classes:
                    counts[int(c)] += 1
    except Exception:
        counts = [0] * num_classes

    # Tính thời gian đèn theo số lượng xe
    total_vehicles = sum(counts)

    if 0 < total_vehicles < 5:
        total_seconds = 20
        cmd = "m1"
    elif 5 <= total_vehicles <= 10:
        total_seconds = 45
        cmd = "m2"
    elif 10 < total_vehicles <= 20:
        total_seconds = 60
        cmd = "m3"
    elif total_vehicles > 20:
        total_seconds = 90
        cmd = "m4"
    else:
        total_seconds = 30

    yellow_seconds = 3
    red_seconds = int(total_seconds)
    green_seconds = max(0, red_seconds - yellow_seconds)
    # tạo URL ảnh
    processed_url = url_for('static', filename=f"outputs/{output_filename}", _external=True)
    input_url = url_for('static', filename=f"uploads/{filename}", _external=True)
    return jsonify({
        "processed_image_url": processed_url,
        "input_image_url": input_url,
        "counts": counts,
        "total_seconds": total_seconds,
        "status": "ready",
        "red_seconds": red_seconds,
        "yellow_seconds": yellow_seconds,
        "green_seconds": green_seconds
    })
# -------------------------------------------------------------------------
# CHẠY SERVER FLASK
# -------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
