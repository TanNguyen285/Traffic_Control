import os
import sys
import atexit
import time
import cv2
import threading # Thêm thư viện luồng
from flask import Flask, render_template, jsonify, Response

# Thêm path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

# Import bộ khởi tạo
from khoitao_mt import init_system

app = Flask(__name__)

# Khởi tạo hệ thống một lần duy nhất
engine, cam, Config, ROI_lane = init_system()

# ==========================================
# LUỒNG CHẠY NGẦM TỰ ĐỘNG (ENGINE WORKER)
# ==========================================
import json

# Tạo một biến toàn cầu để lưu kết quả mới nhất
latest_result = None
result_ready = False

@app.route('/stream_results')
def stream_results():
    def event_stream():
        global latest_result, result_ready
        while True:
            # Chỉ khi nào có kết quả mới (result_ready == True) thì mới gửi
            if result_ready:
                yield f"data: {json.dumps(latest_result)}\n\n"
                result_ready = False  # Gửi xong thì reset lại
            time.sleep(0.1) # Nghỉ để không treo CPU

    return Response(event_stream(), mimetype="text/event-stream")

# Trong luồng traffic_engine_worker, bạn cập nhật biến này
def traffic_engine_worker():
    global latest_result, result_ready
    while True:
        res, cmd = engine.thuc_thi_AI()
        if res and res.get("input_image"): # Có kết quả AI thực sự
            latest_result = res
            result_ready = True # Đánh dấu đã có "hàng" mới
        time.sleep(0.3)

# Chạy luồng ngay khi app khởi động
t = threading.Thread(target=traffic_engine_worker, daemon=True)
t.start()
# ==========================================

@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

@app.route('/camera_capture', methods=['POST'])
def camera_capture():
    # Route này giờ chỉ dùng để "ép" chạy ngay lập tức nếu muốn
    res, cmd = engine.thuc_thi_AI() 
    return jsonify(res)

@app.route('/camera_stream')
def camera_stream():
    def gen():
        while True:
            ret, frame = cam.read() 
            if ret and frame is not None:
                frame_to_show = ROI_lane.draw_roi(frame)
                _, jpeg = cv2.imencode('.jpg', frame_to_show)
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            else:
                time.sleep(0.01)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    # Trên Pi nên lấy IP thật để các máy khác truy cập được
    try:
        host_ip = os.popen('hostname -I').read().split()[0]
    except:
        host_ip = "0.0.0.0"
        
    print(f"Server started at: http://{host_ip}:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)