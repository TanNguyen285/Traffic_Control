import os
import sys
import atexit
import time
import cv2
import threading
import json
from flask import Flask, render_template, jsonify, Response, request
from quanly import quanly_log

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "logs"))

from khoitao_mt import init_system

app = Flask(__name__)

# Khởi tạo hệ thống
engine, cam, Config, ROI_lane = init_system()

# Log — khởi tạo TRƯỚC khi dùng ở bất kỳ đâu
json_log = quanly_log(log_dir="logs")

# Kết quả mới nhất để SSE đẩy lên Web
latest_result = None
result_ready  = False

# ==========================================
# API QUẢN LÝ CHẾ ĐỘ & LOG
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
    # Lấy thẳng từ engine — nguồn sự thật duy nhất
    return jsonify({'mode': engine.operation_mode})

# ==========================================
# SSE — chỉ push khi có kết quả mới
# ==========================================

@app.route('/stream_results')
def stream_results():
    def event_stream():
        global latest_result, result_ready

        # Gửi lịch sử ngay khi client kết nối để nạp chart
        yield f"data: {json.dumps(json_log.data_list)}\n\n"

        while True:
            if result_ready and latest_result:
                yield f"data: {json.dumps(latest_result)}\n\n"
                result_ready = False
            time.sleep(0.1)

    return Response(event_stream(), mimetype="text/event-stream")

# ==========================================
# WORKER — chỉ chạy khi bien_run=True
# ==========================================

def uart_event_worker():
    global latest_result, result_ready
    while True:
        if engine.bien_run:
            print("\n" + "="*50)
            print(f"[DEBUG SYSTEM] BẮT ĐẦU CHU KỲ AI - Chế độ: {engine.operation_mode.upper()}")
            print("="*50)

            # Thực thi AI
            # Lưu ý: Nếu kẹt, hàm này sẽ kẹt trong vòng lặp 'while self.ket_local' bên trong engine
            result_new, cmd = engine.thuc_thi_AI()

            if result_new is not None:
                latest_result = result_new
                result_ready = True
                
                # In thông tin giao tiếp Ethernet
                print(f"--- THÔNG SỐ GIAO TIẾP ---")
                print(f"  > Kết nối Trạm kia: {'[OK]' if result_new['remote_connected'] else '[MẤT KẾT NỐI]联'}")
                print(f"  > Trạm Local ({engine.id}): {result_new['cnn_status']} | {result_new['xe_local']} xe")
                
                if result_new['remote_connected']:
                    print(f"  > Trạm Remote: {'KẸT' if result_new['remote_jam'] else 'THOÁNG'} | {result_new['xe_remote']} xe")
                
                print(f"  > LỆNH CUỐI (UART): {cmd}")
                print("="*50 + "\n")
                
            # Reset biến run để chờ lệnh tiếp theo từ UART/Web
            engine.bien_run = False 
            
        time.sleep(0.1)
t = threading.Thread(target=uart_event_worker, daemon=True)
t.start()
print("[APP] Worker khởi động — chờ tín hiệu run từ UART...")

# ==========================================
# ROUTE CAMERA & MANUAL
# ==========================================

@app.route("/")
def index():
    return render_template("index.html", class_names=Config.YOLO_CLASSES)

@app.route('/manual_run', methods=['POST'])
def manual_run():
    data   = request.get_json()
    signal = data.get('signal', 'run')
    print(f"[MANUAL] Trigger '{signal}' từ Web")
    engine.uart_esp32_rasp(signal)
    return jsonify({'status': 'ok', 'signal': signal})

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