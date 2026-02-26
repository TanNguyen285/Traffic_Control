from flask import Flask, render_template, jsonify, Response, request
from ultralytics import YOLO
import os, atexit, platform, cv2
import numpy as np

# ==========================================================
# 1. IMPORT MODULES
# ==========================================================
from camera import Camera
from yoloxx import Yolo_AI
from uart_service import UARTService
from pre_processor_image import Tienxulyanh

# ==========================================================
# 2. PATH CONFIG
# ==========================================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = "runs/detect/yolov26_trained/weights/best.pt"

STATIC_DIR = os.path.join(APP_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
OUTPUT_DIR = os.path.join(STATIC_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================================
# 3. INIT
# ==========================================================
app = Flask(__name__, static_folder=STATIC_DIR)

# Load YOLO
try:
    model = YOLO(MODEL_PATH)
    print(f"✅ Load Model OK: {MODEL_PATH}")
except Exception as e:
    print(f"❌ Load Model Fail: {e}")
    model = None

cam = Camera(src=0)
pre_proc = Tienxulyanh(target_size=(640, 640))
ai = Yolo_AI(model, class_names=['bus', 'car', 'motorbike', 'truck'])

uart_port = "/dev/ttyAMA0" if platform.system() == "Linux" else "COM3"
uart = UARTService(port=uart_port)

cam.start()

selected_image = None

# ==========================================================
# 4. SIGNAL LOGIC (DUY NHẤT 1 CHỖ TÍNH CMD)
# ==========================================================
def calculate_signal(total):
    if total < 5:
        return 20, "m1"
    elif total <= 10:
        return 45, "m2"
    elif total <= 20:
        return 60, "m3"
    else:
        return 90, "m4"

# ==========================================================
# 5. CORE DETECTION PIPELINE
# ==========================================================
def perform_detection():
    global selected_image

    if model is None:
        return {"error": "Model not loaded"}, "m0"

    # ===== 1. Lấy ảnh =====
    if selected_image is not None:
        print("[DETECT] Xử lý ảnh upload")
        frame = selected_image.copy()
        selected_image = None
    else:
        ret, frame = cam.read()
        if not ret:
            return {"error": "Camera không khả dụng"}, "m0"

    # ===== 2. Preprocess =====
    try:
        ready_frame, brightness = pre_proc.process(
            frame,
            roi_box=[0.1, 0.9, 0.0, 1.0]
        )
    except Exception as e:
        return {"error": f"Lỗi tiền xử lý: {e}"}, "m0"

    # ===== 3. Detect =====
    try:
        result, total = ai.detect(ready_frame, brightness)
    except Exception as e:
        return {"error": f"Lỗi detect: {e}"}, "m0"

    if result.get("error"):
        return result, "m0"

    # add original image as base64 (to avoid saving disk)
    try:
        import base64
        _, buf = cv2.imencode('.jpg', frame)
        b64 = base64.b64encode(buf).decode('utf-8')
        result['input_image'] = f"data:image/jpeg;base64,{b64}"
    except Exception:
        pass

    # ===== 4. Tính tín hiệu =====
    total_seconds, cmd = calculate_signal(total)

    result["total_seconds"] = total_seconds
    result["green_seconds"] = max(0, total_seconds - 3)

    # ===== 5. Gửi UART =====
    uart.send(cmd)

    return result, cmd

# ==========================================================
# 6. ROUTES
# ==========================================================
@app.route("/")
def index():
    # pass class names to template so counts boxes match app logic
    return render_template("index.html", class_names=['bus', 'car', 'motorbike', 'truck'])

@app.route('/camera_stream')
def camera_stream():
    def gen():
        while True:
            ret, frame = cam.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       jpeg.tobytes() + b'\r\n')
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    res, _ = perform_detection()
    return jsonify(res)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global selected_image

    try:
        if 'file' not in request.files:
            return jsonify({"error": "Không có file"}), 400

        file = request.files['file']
        nparr = np.frombuffer(file.read(), np.uint8)
        selected_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if selected_image is None:
            return jsonify({"error": "Lỗi đọc ảnh"}), 400

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear_selected_image', methods=['POST'])
def clear_selected_image():
    global selected_image
    selected_image = None
    return jsonify({"success": True}), 200

# ==========================================================
# 7. UART TRIGGER
# ==========================================================
def on_uart_trigger():
    print("[SYSTEM] UART trigger")
    perform_detection()

uart.start_listening(on_uart_trigger)

# ==========================================================
# 8. CLEANUP
# ==========================================================
atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)