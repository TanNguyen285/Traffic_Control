import os
import sys
import atexit
import time
import cv2
import threading # Thêm thư viện luồng
from flask import Flask, render_template, jsonify, send_from_directory, Response, request
from quanly import quanly_log

# Thêm path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Thư mục TRAM_A
LOG_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "logs")) 

# Kiểm tra log cho chắc chắn khi khởi động
print(f"📂 Log folder path: {LOG_FOLDER}")
# Import bộ khởi tạo
from khoitao_mt import init_system

app = Flask(__name__)

# Khởi tạo hệ thống một lần duy nhất
engine, cam, Config, ROI_lane = init_system()

# ==========================================
# CHẾ ĐỘ HOẠT ĐỘNG (Single or Branch)
# ==========================================
current_mode = "single"  # "single" hoặc "branch"

# ==========================================
# LUỒNG CHẠY Log_data_json
# ==========================================
@app.route('/get_log_data')
def get_log_data():
    # Kỹ thuật chuyên nghiệp: Trả về dữ liệu từ RAM để đạt tốc độ cao nhất
    # json_log.data_list luôn chứa dữ liệu mới nhất mà worker vừa ghi
    try:
        if json_log and hasattr(json_log, 'data_list'):
            return jsonify(json_log.data_list)
        return jsonify([])
    except Exception as e:
        print(f"Lỗi lấy dữ liệu từ RAM: {e}")
        return jsonify([])

# ==========================================
# CHẾ ĐỘ HOẠT ĐỘNG API
# ==========================================
@app.route('/set_mode', methods=['POST'])
def set_mode():
    global current_mode
    data = request.get_json()
    mode = data.get('mode', 'single')
    
    if mode not in ['single', 'branch']:
        return jsonify({'error': 'Invalid mode'}), 400
    
    current_mode = mode
    engine.set_mode(mode)
    
    print(f"[MODE] Chế độ hoạt động thay đổi thành: {mode}")
    return jsonify({'status': 'ok', 'mode': mode})

@app.route('/get_mode')
def get_mode():
    return jsonify({'mode': current_mode})

# ==========================================
# LUỒNG CHẠY Kết quau AI (SSE)
# ==========================================
import json
# Tạo một biến toàn cầu để lưu kết quả mới nhất
latest_result = None
result_ready = False
# Nhận dữ liệu từ engine và cập nhật vào log, đồng thời đánh dấu đã có kết quả mới
@app.route('/stream_results')
def stream_results():
    def event_stream():
        global latest_result, result_ready
        
        # 1. Gửi lịch sử ngay khi Client vừa kết nối để nạp Chart
        # json_log.data_list là list chứa các dict từ file logs
        yield f"data: {json.dumps(json_log.data_list)}\n\n"
        
        while True:
            if result_ready:
                # 2. Bắn data realtime để "kích" JS chạy hàm ảnh và đọc file JSON
                yield f"data: {json.dumps(latest_result)}\n\n"
                result_ready = False
            time.sleep(0.1)
    return Response(event_stream(), mimetype="text/event-stream")
json_log = quanly_log(log_dir="logs")

# ==========================================
# LUỒNG CHẠY NGẦM TỰ ĐỘNG (ENGINE WORKER)
# ==========================================

# Trong luồng traffic_engine_worker, bạn cập nhật biến này
def traffic_engine_worker():
    global latest_result, result_ready
    while True:
        # result_new lúc này là cái dict chứa link ảnh và số lượng xe
        result_new, cmd = engine.thuc_thi_AI()

        if result_new is not None: 
            # Cập nhật log số liệu
            json_log.update_storage(result_new)
            
            # Gán kết quả để SSE hốt đi
            latest_result = result_new
            result_ready = True 
            print(f"🚀 Đã có kết quả mới: {result_new['xe_local']} xe") # Thêm dòng này để debug
        
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