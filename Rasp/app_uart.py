import os
import sys
import atexit
import time
import cv2
import threading
import queue
import json
from flask import Flask, render_template, jsonify, Response, request
from quanly import quanly_log

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))

from khoitao_mt import init_system

app = Flask(__name__)

engine, cam, Config, ROI_lane = init_system()
json_log = quanly_log(log_dir="logs")

sse_queue = queue.Queue(maxsize=100)

def push_sse(payload: dict):
    try:
        sse_queue.put_nowait(payload)
    except queue.Full:
        pass

# ==========================================
# API
# ==========================================

@app.route('/get_log_data')
def get_log_data():
    try:
        if json_log and hasattr(json_log, 'data_list'):
            return jsonify(json_log.data_list)
        return jsonify([])
    except Exception as e:
        print(f"Lỗi lấy dữ liệu từ RAM: {e}")
        return jsonify([])

@app.route('/set_mode', methods=['POST'])
def set_mode():
    data = request.get_json()
    mode = data.get('mode', 'single')
    if mode not in ['single', 'branch']:
        return jsonify({'error': 'Invalid mode'}), 400
    engine.set_mode(mode)
    return jsonify({'status': 'ok', 'mode': mode})

@app.route('/get_mode')
def get_mode():
    return jsonify({'mode': engine.operation_mode})

# ==========================================
# SSE
# ==========================================

@app.route('/stream_results')
def stream_results():
    def event_stream():
        yield f"data: {json.dumps(json_log.data_list)}\n\n"
        while True:
            try:
                payload = sse_queue.get(block=True, timeout=0.5)
                yield f"data: {json.dumps(payload)}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"

    resp = Response(event_stream(), mimetype="text/event-stream")
    resp.headers["Cache-Control"]     = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp

# ==========================================
# WORKER
# ==========================================

def uart_event_worker():
    while True:
        if engine.bien_run:
            print("\n" + "="*50)
            print(f"[DEBUG SYSTEM] BẮT ĐẦU CHU KỲ AI - Chế độ: {engine.operation_mode.upper()}")
            print("="*50)

            result_new, cmd = engine.thuc_thi_AI()

            if result_new is not None:
                result_new["time"] = time.strftime("%H:%M:%S")
                json_log.update_storage(result_new)
                push_sse(result_new)

                print(f"--- THÔNG SỐ GIAO TIẾP ---")
                print(f"  > Kết nối Trạm kia: {'[OK]' if result_new['remote_connected'] else '[MẤT KẾT NỐI]'}")
                print(f"  > Trạm Local ({engine.id}): {result_new['cnn_status']} | {result_new['xe_local']} xe")
                if result_new['remote_connected']:
                    print(f"  > Trạm Remote: {'KẸT' if result_new['remote_jam'] else 'THOÁNG'} | {result_new['xe_remote']} xe")
                print(f"  > LỆNH CUỐI (UART): {cmd}")
                print("="*50 + "\n")

            engine.bien_run = False

        time.sleep(0.1)

t = threading.Thread(target=uart_event_worker, daemon=True)
t.start()
print("[APP] Worker khởi động — chờ tín hiệu run từ UART...")

# ==========================================
# ROUTE CAMERA
# ==========================================

@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

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
                time.sleep(0.1)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

atexit.register(lambda: cam.stop())

if __name__ == "__main__":
    try:
        host_ip = os.popen('hostname -I').read().split()[0]
    except:
        host_ip = "0.0.0.0"
    print(f"🌐 Dashboard: http://{host_ip}:8000")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)