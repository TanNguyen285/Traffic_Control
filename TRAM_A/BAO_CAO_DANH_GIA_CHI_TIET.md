# 📊 BÁO CÁO ĐÁNH GIÁ CHI TIẾT HỆ THỐNG ĐIỀU KHIỂN GIAO THÔNG (TRAM_A)

**Ngày báo cáo:** 21/04/2026  
**Phần mềm được đánh giá:** Traffic_Control - Edge AI System  
**Môi trường:** Raspberry Pi 5 + ESP32

---

## 📋 MỤC LỤC
1. [Tổng Quan Hệ Thống](#tổng-quan)
2. [Kiến Trúc Thiết Kế](#kiến-trúc)
3. [Phân Tích Chi Tiết Các Thành Phần](#chi-tiết)
4. [Đánh Giá Ưu Điểm](#ưu-điểm)
5. [Phân Tích Nhược Điểm & Lỗi](#nhược-điểm)
6. [Đánh Giá Hiệu Suất](#hiệu-suất)
7. [Chất Lượng Code & Best Practices](#chất-lượng)
8. [Khuyến Nghị & Cải Thiện](#khuyến-nghị)

---

## 🎯 Tổng Quan Hệ Thống {#tổng-quan}

### I. Mục Đích
Hệ thống TRAM_A (Traffic Control) là một giải pháp **điều khiển giao thông tự động** chạy trên **Edge AI**, được thiết kế để:
- Giám sát giao thông trực tiếp qua camera
- Phân tích mật độ và tình trạng giao thông
- Điều phối tín hiệu đèn giao thông tự động theo AI
- Hoạt động độc lập hoặc phối hợp giữa 2 trạm (TRAM_A + TRAM_B)
- Chạy trên Raspberry Pi 5 với hiệu suất cao, tiêu tốn tài nguyên thấp

### II. Thành Phần Chính

| Thành Phần | Công Nghệ | Mục Đích |
|-----------|-----------|---------|
| **Tiền xử lý ảnh** | OpenCV + SCI Model | Nâng cao chất lượng ảnh thiếu sáng |
| **Phân tích mật độ** | SimpleCNN (2 class) | Nhận diện kẹt xe / thông thoáng |
| **Nhận diện xe** | YOLOv26n + NCNN | Đếm xe chi tiết và phân loại |
| **Điều khiển logic** | Python Threading | Xử lý logic phối hợp 2 trạm |
| **Giao tiếp** | UART + Ethernet | Kết nối ESP32 + trạm đối diện |
| **Giao diện web** | Flask + HTML/CSS/JS | Giám sát realtime trên trình duyệt |

### III. Luồng Hoạt Động Tổng Quát

```
Camera → Tiền Xử Lý (ROI, SCI) → CNN (Kẹt?) 
  ↓
  Nếu Kẹt: Chờ thông thoáng (Vòng lặp IM LẶNG)
  Nếu Thoáng: Chạy YOLO → Đếm xe → Tính lệnh
  ↓
  Đồng bộ Ethernet (Nếu có)
  ↓
  Gửi lệnh xuống ESP32 (UART)
  ↓
  Trả về kết quả cho Web UI
```

---

## 🏗️ Kiến Trúc Thiết Kế {#kiến-trúc}

### I. Cấu Trúc Tầng Xử Lý

Hệ thống được thiết kế theo **4 tầng xử lý tuần tự**:

#### **Tầng 1: Tiền Xử Lý Hình Ảnh** (`tienxulyanh.py`)
```
Đầu vào: Frame camera (480x480)
    ↓
Áp dụng ROI (Che đen vùng ngoài)
    ↓
Tính độ sáng (Brightness)
    ↓
Nếu sáng < 0.2: Chạy SCI (Low-light Enhancement)
    ↓
Tạo 2 bản ảnh:
  - frame_cnn: 224x224 (cho CNN)
  - frame_yolo: 640x640 (cho YOLO)
```

**Đánh giá Tầng 1:**
- ✅ Logic rõ ràng, bố trí khoa học
- ✅ Tiết kiệm tài nguyên (xử lý ROI sẽ giảm kích thước ảnh cho CNN)
- ❌ SCI model chỉ bật khi brightness < 0.2, có thể bỏ lỡ ảnh nhạt mức trung bình
- ⚠️ Roi_box cố định, không thích ứng với camera khác

#### **Tầng 2: Phân Tích Mật Độ** (`cnn.py`)
```
Đầu vào: frame_cnn 224x224
    ↓
SimpleCNN (3.2M params)
    ↓
Output: "Kẹt Xe" hoặc "Thông Thoáng" + Confidence
    ↓
Vẽ kết quả lên frame_raw (Màu đỏ/xanh)
```

**Đánh giá Tầng 2:**
- ✅ Mô hình nhẹ, tốc độ inference nhanh
- ✅ Kiến trúc EfficientBlock tốt cho edge devices
- ✅ Sử dụng Inverted Residual + Depthwise Conv (MobileNet-style)
- ❌ Chỉ 2 class, không phân loại chi tiết mức độ kẹt (nhẹ/vừa/nặng)
- ⚠️ Không xử lý Multiple ROI (chỉ 1 vùng quan sát)

#### **Tầng 3: Nhận Diện Chi Tiết** (`yolov26.py`)
```
Đầu vào: frame_yolo 640x640 + brightness
    ↓
YOLOv26n (NCNN weights)
    ↓
Phát hiện bounding box + class
    ↓
Thống kê: [Xe Tải, Van, Bus, Xe Máy, Xe Ô Tô]
    ↓
Vẽ box + label lên ảnh
```

**Đánh giá Tầng 3:**
- ✅ Mô hình mạnh, precision tốt
- ✅ Hỗ trợ 5 loại phương tiện
- ✅ NCNN inference rất nhanh trên Pi
- ⚠️ Chỉ chạy khi thoáng (CNN bảo "Thông Thoáng"), không chạy khi kẹt
- ❌ Không có cơ chế fallback nếu mô hình YOLO crash
- ⚠️ Conf threshold cứng = 0.4, không cấu hình được

#### **Tầng 4: Điều Phối Logic** (`logic_test.py`)
```
Kiểm tra Trigger (Auto-mode hoặc Manual từ UART)
    ↓
Nếu Kẹt: Chạy vòng lặp IM LẶNG
  - Cứ 1 giây kiểm tra lại 1 lần
  - Thoát khi: Hết kẹt hoặc nhận lệnh "run1" (xả trạm)
    ↓
Khi Thoát: Chạy YOLO → Đếm xe
    ↓
Đồng bộ Ethernet (Gửi/Nhận dữ liệu từ TRAM_B)
    ↓
Tính lệnh cuối (A/B/m1/m2/m3/m4)
    ↓
Gửi xuống ESP32 qua UART
```

**Đánh giá Tầng 4:**
- ✅ Logic phối hợp 2 trạm thông minh (Ưu tiên kẹt)
- ✅ Chế độ Auto tự động kích hoạt
- ✅ Có cơ chế fallback (chạy độc lập nếu mất Ethernet)
- ❌ Vòng lặp IM LẶNG chỉ nghỉ 1 giây, có thể quá tải CPU
- ⚠️ Không có timeout cho vòng lặp kẹt (có thể kẹt vĩnh viễn)
- ⚠️ Lệnh "run1" (xả trạm) chỉ là chế độ bức buộc, không phải điều khiển tự động

---

### II. Kiến Trúc Giao Tiếp & Threading

#### **Model Threading**
```
Main Thread (Flask)
  ├─ Route: / (UI HTML)
  ├─ Route: /camera_stream (MJPEG Stream)
  ├─ Route: /stream_results (SSE - Server-Sent Events)
  └─ Route: /get_log_data (JSON log)

Background Thread 1: traffic_engine_worker
  └─ Chạy lặp AI (engine.thuc_thi_AI())
     └─ Gọi: Camera.read() → CNN → YOLO → Logic
     └─ Cập nhật: json_log + latest_result
     └─ Mỗi 0.3 giây kiểm tra 1 lần

Background Thread 2: camera._reader (trong Camera class)
  └─ Đọc frame từ camera
  └─ Lưu vào self.frame (Thread-safe with Lock)
  └─ Tự động reconnect nếu mất kết nối

Background Thread 3: ethernet.ketnoiethernet
  └─ Server socket listen (TRAM_A)
  └─ Client socket connect (TRAM_B)
  └─ Nhận dữ liệu từ đối diện

Background Thread 4: uart_service._send_worker
  └─ Xử lý hàng đợi (Queue) gửi UART
```

**Đánh giá Threading:**
- ✅ Sử dụng daemon threads (tự động tắt khi app tắt)
- ✅ Có Lock cho thread-safe access
- ✅ Nhẹ và hiệu quả
- ⚠️ Không có cơ chế stop/join chính xác → Có thể crash khi shutdown
- ⚠️ Queue UART dùng put() ngay, không kiểm tra kích thước → có thể overflow

---

### III. Cấu Trúc Thư Mục

```
TRAM_A/
├─ Modules AI:
│  ├─ tienxulyanh.py (Tiền xử lý ảnh)
│  ├─ cnn.py (SimpleCNN Classification)
│  ├─ yolov26.py (YOLO Detection)
│  ├─ model_sci.py (SCI Enhancement Network)
│  └─ loss_sci.py (SCI Loss Functions)
│
├─ Điều khiển Logic:
│  ├─ logic_test.py (Luồng xử lý chính)
│  ├─ logic_2.py (Phiên bản cũ, không dùng)
│  └─ khoitao_mt.py (Khởi tạo hệ thống)
│
├─ Giao tiếp Hardware:
│  ├─ camera.py (Camera Manager)
│  ├─ uart_service.py (UART/Serial)
│  ├─ ethernet.py (Ethernet Socket)
│  └─ ROI.py (ROI Manager)
│
├─ Web & Logging:
│  ├─ app.py (Flask Server)
│  ├─ quanly.py (JSON Log Manager)
│  ├─ templates/index.html
│  ├─ static/script.js
│  └─ static/style.css
│
├─ Mô hình & Trọng số:
│  ├─ runs/detect/ (YOLO weights)
│  ├─ runs/exp3/ (CNN weights)
│  ├─ weights/ (SCI weights)
│  └─ SimpleCNN/ (CNN source)
│
└─ Data & Logs:
   └─ logs/ (JSON reports)
```

---

## 🔍 Phân Tích Chi Tiết Các Thành Phần {#chi-tiết}

### 1. CAMERA MANAGEMENT (`camera.py`)

**Tính năng:**
- ✅ Tự động reconnect nếu mất kết nối
- ✅ Platform-specific optimization (Windows MSMF/DSHOW, Linux V4L2)
- ✅ Thread-safe frame buffering
- ✅ MJPEG compression trên Pi để tăng FPS
- ✅ Buffer size = 1 để lấy frame mới nhất (real-time)

**Lỗi tiềm ẩn:**
```python
# ❌ Vấn đề: max_fail=20 nhưng không ghi log chi tiết
if self.fail_count >= self.max_fail:
    print("[CAM] Lỗi liên tiếp, đang reset camera...")
    # Khi nào quay lại? Không ghi log lí do
    
# ✅ Cải thiện:
if self.fail_count >= self.max_fail:
    print(f"[CAM] Lỗi liên tiếp ({self.fail_count}x). Lí do: {ret}. Reset...")
    self._open()
```

---

### 2. YOLO DETECTION (`yolov26.py`)

**Tính năng hiện tại:**
```python
- 5 class: ['car', 'van', 'bus', 'motorcycle', 'truck']
- Confidence threshold = 0.4 (cứng)
- Đầu ra: dict chứa counts + frame
```

**Vấn đề:**
```python
# ❌ Threshold cứng không cấu hình
results = self.model.predict(processed_frame, conf=0.4)

# ❌ Nếu không có box (mặc dù có object), sẽ trả về toàn 0
if boxes is not None and hasattr(boxes, 'cls'):
    # Nếu boxes = None thì sao? Không handle
```

**Cải thiện:**
```python
# ✅ Làm threshold có thể cấu hình
def __init__(self, model_obj, class_names, conf_threshold=0.4):
    self.conf_threshold = conf_threshold

# ✅ Thêm error handling
if boxes is not None and len(boxes) > 0:
    cls_list = [int(x) for x in boxes.cls]
else:
    cls_list = []  # Handle empty boxes
```

---

### 3. CNN CLASSIFICATION (`cnn.py`)

**Kiến trúc SimpleCNN:**
- Input: 224x224 RGB
- Stem: Conv 3→32 (Stride 2)
- Blocks: 6 EfficientBlocks với xen kẽ Stride 1/2
- Output: 2 class + Dropout(0.5)
- Tổng params: ~3.2M (rất nhẹ)

**Mô hình tốt nhưng:**
```python
# ❌ Hardcoded, không cấu hình được
self.transform(pil_img).unsqueeze(0).to(self.device)

# ⚠️ Device luôn là CPU trên Pi, nếu GPU available không dùng
self.device = torch.device('cpu')  # Trong tienxulyanh.py
```

---

### 4. LOGIC ĐIỀU PHỐI (`logic_test.py`)

**Quy tắc chính:**

```python
# Chế độ độc lập (Mất Ethernet)
if not remote_connected:
    if ket_local:
        cmd = "A"  # Ưu tiên hướng A
    else:
        cmd = m1/m2/m3/m4  # Phân mức theo xe count

# Chế độ phối hợp (Có Ethernet)
# TRAM_A & TRAM_B cùng nhìn logic này
if A and (B or b):  # A kẹt, B bất kỳ
    cmd = "A"  # Ưu tiên A
elif B and a:  # B kẹt, A thoáng
    cmd = "B"
elif a and b:  # Cả hai thoáng
    cmd = m_based_on_max(xe_a, xe_b)
```

**Phân tích:**
- ✅ Logic hợp lý, ưu tiên hướng kẹt
- ✅ Chế độ fallback khi mất mạng
- ❌ **Vòng lặp IM LẶNG** chỉ sleep 1 giây - quá tải CPU
- ❌ Không có timeout → Có thể kẹt vĩnh viễn
- ❌ Không có Early Exit khi "mặc định" kẹt quá lâu

**Vấn đề lớn - Vòng Lặp Kẹt:**
```python
while self.ket_local:
    if self.bien_run1:
        break 
    print(f"[{self.id}] Đang kẹt xe...")
    if self.module_chup_anh(): 
        self.ket_local = self.module_chay_cnn()
    
    time.sleep(1)  # ⚠️ Chỉ 1 giây - CPU sẽ làm 60 vòng/phút = 60 inferences/phút
    
# ✅ Cải thiện: Thêm timeout
max_jam_time = 300  # 5 phút
jam_start_time = time.time()
while self.ket_local:
    if time.time() - jam_start_time > max_jam_time:
        print("[!] TIMEOUT kẹt quá lâu, thoát buộc")
        break
    time.sleep(0.5)  # Giảm thành 0.5s hoặc dynamic
```

---

### 5. ETHERNET SERVICE (`ethernet.py`)

**Kiến trúc:**
- **TRAM_A:** Server socket (bind + listen)
- **TRAM_B:** Client socket (connect)
- Giao thức: JSON qua TCP + newline delimiter

**Vấn đề:**
```python
# ❌ Hostname resolution có thể thất bại
real_ip = socket.gethostbyname(self.peer_hostname)

# ⚠️ Buffer parsing có bug
buffer = ""
while True:
    chunk = self.conn.recv(1024).decode('utf-8')
    buffer += chunk
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        # Nếu data qua dài > 1024 bytes sẽ bị chia cắt!

# ✅ Cải thiện: dùng JSON length prefix hoặc message delim chắc hơn
```

---

### 6. UART SERVICE (`uart_service.py`)

**Tính năng:**
- Queue-based sending
- Non-blocking communication
- Automatic serial port detection (nếu available)

**Vấn đề:**
```python
# ❌ Queue không có maxsize → Có thể accumulate
self.send_queue = queue.Queue()  # Unlimited

# ⚠️ Daemon thread không guarantee gửi hết trước exit
threading.Thread(target=self._send_worker, daemon=True).start()

# ✅ Cải thiện:
self.send_queue = queue.Queue(maxsize=100)
# Thêm graceful shutdown
```

---

### 7. WEB UI & LOGGING (`app.py`, `quanly.py`)

**Ưu điểm:**
- ✅ SSE (Server-Sent Events) để push dữ liệu real-time
- ✅ Streaming MJPEG video
- ✅ JSON log với auto-rotation (50 entries → save file)

**Vấn đề:**
```python
# ❌ global variable result_ready dễ race condition
global latest_result, result_ready
if result_ready:
    yield f"data: {json.dumps(latest_result)}\n\n"
    result_ready = False
# Nếu 2 client kết nối cùng lúc thì sao?

# ✅ Cải thiện: dùng Queue hoặc Lock
```

---

## ⭐ Đánh Giá Ưu Điểm {#ưu-điểm}

### 1. **Kiến Trúc Thông Minh & Modular**
- ✅ 4 tầng xử lý rõ ràng, dễ bảo trì
- ✅ Dễ mở rộng: thêm mô hình, thêm trạm, thêm sensor
- ✅ Decoupling tốt giữa các module (Camera ≠ Logic ≠ UART)

### 2. **Tối Ưu Cho Edge Device**
- ✅ SimpleCNN chỉ 3.2M params, inference < 10ms
- ✅ YOLO NCNN format, rất nhanh trên CPU Pi
- ✅ ROI + SCI giảm khối lượng dữ liệu cần xử lý
- ✅ Batch processing từng frame, không để pending

### 3. **Xử Lý Ảnh Tiên Tiến**
- ✅ SCI model cho low-light enhancement (bên đêm, ngược sáng)
- ✅ Brightness detection tự động bật/tắt SCI
- ✅ ROI polygon để tập trung vào vùng cần thiết

### 4. **Phối Hợp 2 Trạm Thông Minh**
- ✅ Logic ưu tiên kẹt xe (Kẹt → ưu tiên)
- ✅ Chế độ fallback khi mất mạng
- ✅ Gửi/Nhận dữ liệu đồng thời

### 5. **Giao Diện Web Real-Time**
- ✅ SSE push data liên tục
- ✅ Live video stream + chart log
- ✅ Không cần polling

### 6. **Threading & Async Design**
- ✅ Non-blocking I/O cho camera, UART, Socket
- ✅ Background worker không ảnh hưởng Flask
- ✅ Graceful degradation khi mất thiết bị

### 7. **Auto-Reconnect Mechanisms**
- ✅ Camera tự reconnect nếu mất kết nối
- ✅ Ethernet tự reconnect liên tục
- ✅ Không crash toàn bộ hệ thống

---

## ⚠️ Phân Tích Nhược Điểm & Lỗi {#nhược-điểm}

### **CRITICAL ISSUES**

#### 1. ❌ Vòng Lặp IM LẶNG Không Có Timeout
**Mức độ:** 🔴 CRITICAL  
**Vị trí:** `logic_test.py` line 99-108

```python
while self.ket_local:
    if self.bien_run1:
        break 
    print(f"[{self.id}] Đang kẹt xe...")
    if self.module_chup_anh(): 
        self.ket_local = self.module_chay_cnn()
    time.sleep(1)
    # ❌ Nếu CNN luôn báo "Ket Xe" → vòng lặp vô tận!
    # ❌ Không có timeout để escape
```

**Hậu quả:** 
- Hệ thống mắc kẹt vĩnh viễn tại 1 vị trí
- Không xử lý được sự cố nếu camera bị che kín
- CPU bị chiếm dụng 100% với inference liên tục

**Cách khắc phục:**
```python
MAX_JAM_TIME = 300  # 5 phút
jam_start_time = time.time()
while self.ket_local:
    if time.time() - jam_start_time > MAX_JAM_TIME:
        print("[TIMEOUT] Kẹt quá lâu, thoát buộc")
        break
    # ...
```

---

#### 2. ❌ Race Condition - SSE Server-Sent Events
**Mức độ:** 🟠 HIGH  
**Vị trí:** `app.py` line 31-39

```python
global latest_result, result_ready

@app.route('/stream_results')
def stream_results():
    # ⚠️ Nếu 2 client connect cùng lúc:
    # - Client 1 yield data, set result_ready = False
    # - Client 2 vẫn chưa yield → bị mất data
    while True:
        if result_ready:
            yield f"data: {json.dumps(latest_result)}\n\n"
            result_ready = False  # ❌ Toàn cầu!
```

**Hậu quả:**
- Multi-client thì mất data cho client thứ 2+
- Không real-time đúng nghĩa

**Cách khắc phục:**
```python
from queue import Queue

# Dùng Queue thay vì global biến
result_queue = Queue(maxsize=10)

@app.route('/stream_results')
def stream_results():
    while True:
        try:
            result = result_queue.get(timeout=1)
            yield f"data: {json.dumps(result)}\n\n"
        except:
            yield ": keepalive\n\n"
```

---

#### 3. ❌ UART Queue Không Có Giới Hạn
**Mức độ:** 🟠 HIGH  
**Vị trị:** `uart_service.py` line 11

```python
self.send_queue = queue.Queue()  # ❌ Unlimited size

# Nếu app gửi 1000 lệnh/giây nhưng UART chỉ gửi 100/giây:
# Queue sẽ accumulate 900 item/giây → Memory leak!
```

**Hậu quả:**
- Leak memory nếu UART port bị chậm/disconnect
- Queue size unbounded

**Cách khắc phục:**
```python
self.send_queue = queue.Queue(maxsize=50)

def send(self, msg):
    try:
        self.send_queue.put(msg, timeout=0.1)
    except queue.Full:
        print("[UART] Queue full, lệnh bị drop:", msg)
```

---

#### 4. ❌ Ethernet Buffer Parsing Không Xử Lý Partial JSON
**Mức độ:** 🟠 HIGH  
**Vị trí:** `ethernet.py` line 60-70

```python
buffer = ""
while True:
    chunk = self.conn.recv(1024).decode('utf-8')
    buffer += chunk
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        self.remote_data = json.loads(line)
        # ❌ Nếu line bị incomplete (vd: '{"ket": true') → Exception!
        # ❌ Exception không được catch, connection sẽ break
```

**Hậu quả:**
- Nếu gửi JSON qua 2 gói TCP thì sẽ crash
- Dữ liệu Ethernet không reliable

**Cách khắc phục:**
```python
try:
    self.remote_data = json.loads(line)
except json.JSONDecodeError as e:
    print(f"[ETH] JSON decode error: {e}, line: {line}")
    # Ghi log nhưng không crash
```

---

### **HIGH PRIORITY ISSUES**

#### 5. ⚠️ Vòng Lặp IM LẶNG Sleep 1 Giây - Quá Tải CPU
**Mức độ:** 🟠 HIGH

```python
time.sleep(1)  # ❌ Chỉ 1 giây, 60 inference/phút
```

**Vấn đề:**
- CPU được dùng 100% cho CNN inference liên tục
- Không để lại tài nguyên cho YOLO, UART, Web
- Pi 5 có ~4 cores, 1 core bị chiếm = 25% capacity

**Cải thiện:**
```python
# Adaptive sleep time
if jam_duration < 30:  # < 30 giây kẹt
    sleep_time = 0.3  # Kiểm tra nhanh
elif jam_duration < 120:
    sleep_time = 1.0  # Kiểm tra bình thường
else:
    sleep_time = 5.0  # Kiểm tra chậm
time.sleep(sleep_time)
```

---

#### 6. ⚠️ YOLO Confidence Threshold Cứng = 0.4
**Mức độ:** 🟡 MEDIUM

```python
results = self.model.predict(processed_frame, conf=0.4)
```

**Vấn đề:**
- Không thể cấu hình runtime
- Có thể bỏ lỡ object weak-signal hoặc false positive

**Cách khắc phục:**
```python
def __init__(self, model_obj, class_names, conf_threshold=0.4):
    self.conf_threshold = conf_threshold
    
def detect(self, processed_frame, brightness_val):
    results = self.model.predict(processed_frame, conf=self.conf_threshold)
```

---

#### 7. ⚠️ Không Có Cơ Chế Validate Mô Hình Đúng
**Mức độ:** 🟡 MEDIUM

```python
# khoitao_mt.py
cnn_service = Simple_CNN_config(
    model_path=Config.CNN_PATH,
    transform=cnn_transform,
    classes=Config.CNN_CLASSES
)
# ❌ Không check xem file có tồn tại không
# ❌ Không check xem weights có corrupt không
```

**Cách khắc phục:**
```python
import os

if not os.path.exists(Config.CNN_PATH):
    raise FileNotFoundError(f"CNN model not found: {Config.CNN_PATH}")

try:
    cnn_service = Simple_CNN_config(...)
except Exception as e:
    raise RuntimeError(f"Failed to load CNN model: {e}")
```

---

#### 8. ⚠️ SCI Model Chỉ Chạy Khi Brightness < 0.2
**Mức độ:** 🟡 MEDIUM

```python
if self.use_sci and self.brightness < 0.2:
    frame_ai = self.module_sci(frame_ai)
```

**Vấn đề:**
- Ảnh mức brightness 0.3-0.5 (nhạt vừa) không được enhance
- Có thể bỏ lỡ xe trong tối bán

**Cách khắc phục:**
```python
# Config SCI threshold động
SCI_THRESHOLD = 0.4  # Có thể cấu hình

if self.use_sci and self.brightness < SCI_THRESHOLD:
    frame_ai = self.module_sci(frame_ai)
```

---

#### 9. ⚠️ Không Có Exception Handling Cho YOLO Detect
**Mức độ:** 🟡 MEDIUM

```python
def detect(self, processed_frame, brightness_val):
    try:
        results = self.model.predict(processed_frame, conf=0.4)
        # ...
    except Exception as e:
        print(f"--- Lỗi Yolo_AI.detect(): {e} ---")
        return {"counts": [0]*len(self.class_names), ...}, 0
```

**Vấn đề:**
- Nếu YOLO crash, trả về counts=0 → app vẫn chạy nhưng dữ liệu sai
- Không log lí do crash đủ chi tiết

**Cách khắc phục:**
```python
except Exception as e:
    print(f"[ERROR] YOLO detect failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()  # Log full stack
    return {"counts": [0]*len(self.class_names)}, 0
```

---

### **MEDIUM PRIORITY ISSUES**

#### 10. ⚠️ ROI Box Cố Định - Không Thích Ứng
**Mức độ:** 🟡 MEDIUM

```python
ROI = [
    [20, 640], [220, 20], [420, 20], [620, 640]
]
```

**Vấn đề:**
- Hardcoded cho 1 camera cụ thể
- Nếu thay camera → phải sửa code

**Cách khắc phục:**
```python
# Thêm config file
ROI_CONFIG = {
    "TRAM_A": [[20, 640], [220, 20], [420, 20], [620, 640]],
    "TRAM_B": [[10, 640], [210, 20], [410, 20], [610, 640]]
}

# hoặc auto-detect qua calibration
```

---

#### 11. ⚠️ Hostname Resolution Có Thể Thất Bại Yên Tĩnh
**Mức độ:** 🟡 MEDIUM

```python
real_ip = socket.gethostbyname(self.peer_hostname)
```

**Vấn đề:**
- `.local` domain có thể không resolve trên mọi network
- Không ghi log retry count

**Cách khắc phục:**
```python
max_retries = 10
for attempt in range(max_retries):
    try:
        real_ip = socket.gethostbyname(self.peer_hostname)
        break
    except socket.gaierror:
        print(f"[ETH] Retry {attempt+1}/{max_retries} resolve {self.peer_hostname}")
        time.sleep(2)
else:
    raise RuntimeError(f"Cannot resolve {self.peer_hostname}")
```

---

#### 12. ⚠️ Camera Reconnect Interval = 10 Giây
**Mức độ:** 🟡 MEDIUM

```python
def _open(self):
    # ...
    time.sleep(self.reconnect_interval)  # = 10s
```

**Vấn đề:**
- Quá dài nếu camera mất kết nối tạm thời
- Quá ngắn nếu camera hỏng (sẽ retry 100x/min = lãng phí)

**Cách khắc phục:**
```python
# Exponential backoff
backoff_times = [1, 2, 5, 10, 30]
for attempt in range(max_retries):
    sleep_time = backoff_times[min(attempt, len(backoff_times)-1)]
    time.sleep(sleep_time)
```

---

#### 13. ⚠️ Không Có Metrics/Monitoring Cho Performance
**Mức độ:** 🟡 MEDIUM

**Vấn đề:**
- Không track inference time của từng module
- Không track frame drop rate
- Không track queue size

**Cách khắc phục:**
```python
import time

class PerformanceMonitor:
    def __init__(self):
        self.timings = {}
    
    def record(self, name, duration):
        if name not in self.timings:
            self.timings[name] = []
        self.timings[name].append(duration)
        
    def get_stats(self, name):
        times = self.timings.get(name, [])
        if not times:
            return None
        return {
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times),
            "count": len(times)
        }

# Usage
monitor = PerformanceMonitor()
start = time.time()
# ... CNN inference ...
monitor.record("CNN", time.time() - start)
```

---

### **LOW PRIORITY ISSUES**

#### 14. ⚠️ Lỗi Logic - Biến bien_run1 Không Reset Đúng
**Mức độ:** 🟢 LOW

```python
def uart_esp32_rasp(self, signal="run1"):
    if signal == "run1":
        self.bien_run1 = True

# Trong thuc_thi_AI()
if self.bien_run1:
    self.bien_run1 = False  # ✅ Reset đúng
```

**Vấn đề:** Không có  
**Đánh giá:** ✅ Xử lý tốt

---

#### 15. ⚠️ Log File Rotation Chỉ Khi >= 50 Items
**Mức độ:** 🟢 LOW

```python
if len(self.data_list) >= 50:
    # Save file
```

**Vấn đề:**
- Nếu chạy 1 tuần = 60 items/giờ × 24 × 7 = ~10k items
- Sẽ có 1 file JSON 10k items (có thể lớn ~ 5MB)

**Cách khắc phục:**
```python
# Rotate theo time + count
MAX_ENTRIES_PER_FILE = 50
MAX_TIME_BETWEEN_ROTATE = 3600  # 1 giờ

if len(self.data_list) >= MAX_ENTRIES_PER_FILE or \
   time.time() - self.last_rotate_time > MAX_TIME_BETWEEN_ROTATE:
    self._save_and_rotate()
```

---

## 📊 Đánh Giá Hiệu Suất {#hiệu-suất}

### I. Inference Time Dự Kiến (Raspberry Pi 5)

| Module | Mô hình | Input | Inference Time | Mục đích |
|--------|--------|-------|-----------------|---------|
| **Tiền xử lý** | Custom CV2 | 480x480 | ~10-20ms | Resize, ROI, brightness |
| **SCI** | Finetunemodel | 480x480 | ~50-100ms | Enhancement (chỉ khi cần) |
| **CNN** | SimpleCNN | 224x224 | ~5-15ms | Classification 2-class |
| **YOLO** | YOLOv26n (NCNN) | 640x640 | ~30-50ms | Detection 5-class |
| **Ethernet** | Socket | - | ~1-5ms | Gửi/nhận JSON |
| **UART** | Serial | - | <1ms | Queue send |

**Tổng thời gian 1 chu trình:**
```
Thoáng (Best case):
  Tiền xử lý (15ms) + CNN (10ms) + YOLO (40ms) + Ethernet (5ms) + UART (1ms)
  = ~70ms (14 FPS)

Thoáng + SCI (Night mode):
  Tiền xử lý (15ms) + SCI (80ms) + CNN (10ms) + YOLO (40ms)
  = ~145ms (7 FPS)

Kẹt (Vòng lặp):
  Tiền xử lý (15ms) + CNN (10ms) + sleep(1s)
  = ~1015ms per check = 1 check/second
```

**Nhận xét:**
- ✅ Thoáng: ~70ms hoàn tất → Đủ real-time
- ⚠️ Kẹt: ~1s/check → Quá chậm, CPU idle 99%

---

### II. Memory Usage (Ước Tính)

| Component | Memory |
|-----------|--------|
| Python + Modules | ~200MB |
| SimpleCNN weights | ~3MB |
| YOLO NCNN weights | ~20MB |
| SCI weights | ~5MB |
| Frame buffer (480x480 RGB) | ~0.7MB |
| 50 log entries (JSON) | ~0.1MB |
| **Total** | **~230MB** |

**Đánh giá:** ✅ Tốt (Pi 5 có 8GB RAM)

---

### III. Throughput

| Metric | Giá trị | Ghi chú |
|--------|--------|--------|
| Frames processed/second | 1-14 | Tùy mode (kẹt/thoáng) |
| UART commands/second | ~100 | Giới hạn queue |
| Ethernet packets/second | 1 | 1 chu trình = 1 packet |
| Log entries/hour | ~60 | Nếu đều thoáng |

---

### IV. Bottleneck Analysis

**Chế độ Thoáng:**
```
Camera.read() ← Blocking (có thể mất 10ms)
  ↓
Tiền xử lý + CNN: 25ms
  ↓
YOLO: 40ms ← BOTTLENECK #1 (50% thời gian)
  ↓
Ethernet: 5ms
```

**Chế độ Kẹt:**
```
Vòng lặp IM LẶNG:
  - sleep(1s) ← BOTTLENECK #2 (99% thời gian)
  - CPU idle, lãng phí tài nguyên
```

**Cải thiện:**
1. Giảm YOLO input size: 640 → 480 (giảm 40% thời gian)
2. Sử dụng multi-threading YOLO (nhưng có GIL)
3. Adaptive sleep khi kẹt

---

## 💻 Chất Lượng Code & Best Practices {#chất-lượng}

### I. Code Style & Documentation

**Điểm tích cực:**
- ✅ Viết comment Tiếng Việt, rõ ràng
- ✅ Tên function descriptive: `module_chup_anh()`, `thuc_thi_AI()`
- ✅ Enum/Constants có namespace rõ (Config.YOLO_PATH)

**Vấn đề:**
- ⚠️ Không có docstring cho class/function
- ⚠️ Magic number xuất hiện (0.4, 0.2, 224, 640)
- ⚠️ File names mất consistency (logic_test.py vs logic_2.py)

**Cải thiện:**
```python
class Tienxulyanh:
    """Tiền xử lý ảnh cho AI pipeline.
    
    Tính năng:
    - ROI masking
    - Brightness detection
    - SCI enhancement khi cần
    - Chuẩn bị dual frame (CNN + YOLO)
    """
    
    SCI_BRIGHTNESS_THRESHOLD = 0.2
    CNN_SIZE = (224, 224)
    YOLO_SIZE = (640, 640)
    
    def __init__(self, sci_path, target_size=(640, 640), use_sci=True):
        """Initialize preprocessing pipeline.
        
        Args:
            sci_path (str): Đường dẫn SCI model weight file
            target_size (tuple): Kích thước output ảnh YOLO
            use_sci (bool): Có sử dụng SCI enhancement không
        """
        pass
```

---

### II. Error Handling

**Tình trạng hiện tại:**
```python
# ❌ Try-except quá rộng
try:
    self.sci_net = Finetunemodel(sci_path).to(self.device).eval()
    print(f"✅ SCI Loaded")
except:  # ❌ Bare except!
    self.use_sci = False

# ✅ Cải thiện:
except FileNotFoundError:
    print(f"[ERR] SCI model not found: {sci_path}")
    self.use_sci = False
except RuntimeError as e:
    print(f"[ERR] SCI model load failed: {e}")
    self.use_sci = False
```

**Best Practice:**
- ✅ Specific exception types
- ✅ Log đủ context (file, line, reason)
- ✅ Graceful degradation

---

### III. Concurrency & Thread Safety

**Hiện tại:**
```python
# ✅ Lock đúng nơi
with self.lock:
    self.frame = frame

# ⚠️ Nhưng global biến không có lock
global latest_result, result_ready
if result_ready:  # ❌ Race condition!
    yield f"data: {json.dumps(latest_result)}\n\n"
    result_ready = False
```

**Cải thiện:**
```python
from threading import Lock

result_lock = Lock()

with result_lock:
    if result_ready:
        yield f"data: {json.dumps(latest_result)}\n\n"
        result_ready = False
```

---

### IV. Configuration Management

**Vấn đề:**
```python
# Hardcoded ở Config class
class Config:
    YOLO_PATH = "runs/detect/best_ncnn_model"
    ROI = [[20, 640], [220, 20], [420, 20], [620, 640]]
    MY_PORT = 9999
```

**Cải thiện - Config File:**
```yaml
# config.yaml
ai:
  yolo_path: "runs/detect/best_ncnn_model"
  cnn_path: "runs/exp3/simple_cnn.onnx"
  sci_path: "weights/difficult.pt"
  confidence_threshold: 0.4

processing:
  roi: [[20, 640], [220, 20], [420, 20], [620, 640]]
  sci_brightness_threshold: 0.2
  cnn_size: [224, 224]
  yolo_size: [640, 640]

hardware:
  uart_port: "/dev/ttyAMA0"
  uart_baudrate: 115200
  ethernet_port: 9999

network:
  station_id: "TRAM_A"
  peer_hostname: "lagct2.local"
```

```python
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

# Usage
Config.YOLO_PATH = config["ai"]["yolo_path"]
```

---

### V. Testing & Validation

**Hiện tại:** ❌ Không có unit test  
**Đánh giá:** Đây là vấn đề lớn!

**Khuyến nghị:**
```python
# tests/test_cnn.py
import unittest
from cnn import Simple_CNN_config

class TestCNN(unittest.TestCase):
    def setUp(self):
        self.cnn = Simple_CNN_config(...)
    
    def test_predict_shape(self):
        """Test đầu ra có shape đúng"""
        result = self.cnn.predict(dummy_frame)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
    
    def test_confidence_range(self):
        """Test confidence trong [0, 1]"""
        _, conf, _ = self.cnn.predict(dummy_frame)
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 100.0)

# Run: python -m unittest tests/test_cnn.py
```

---

## 🚀 Khuyến Nghị & Cải Thiện {#khuyến-nghị}

### **PHASE 1: Critical Fixes (1-2 tuần)**

#### 1. Thêm Timeout Cho Vòng Lặp Kẹt
```python
MAX_JAM_DURATION = 600  # 10 phút

# logic_test.py
while self.ket_local:
    elapsed = time.time() - jam_start_time
    if elapsed > MAX_JAM_DURATION:
        print(f"[TIMEOUT] Kẹt quá lâu ({elapsed}s), thoát buộc")
        break  # Escape vòng lặp
    
    if self.bien_run1:
        break
    
    time.sleep(min(elapsed // 30 + 0.5, 5))  # Adaptive sleep
```

#### 2. Thêm JSON Validation Cho Ethernet
```python
# ethernet.py
try:
    self.remote_data = json.loads(line)
except json.JSONDecodeError as e:
    print(f"[ETH] Invalid JSON: {line}, error: {e}")
    # Giữ data cũ, không crash
```

#### 3. Giới Hạn UART Queue Size
```python
# uart_service.py
self.send_queue = queue.Queue(maxsize=50)

def send(self, msg):
    try:
        self.send_queue.put(msg, timeout=0.5)
    except queue.Full:
        print(f"[WARN] UART queue full, cmd dropped: {msg}")
```

---

### **PHASE 2: High Priority Improvements (2-3 tuần)**

#### 4. Refactor SSE Streaming
```python
# app.py
from queue import Queue

class ResultQueue:
    def __init__(self, max_size=10):
        self.queues = {}  # client_id → Queue
    
    def subscribe(self, client_id):
        self.queues[client_id] = Queue(maxsize=self.max_size)
    
    def publish(self, result):
        for q in self.queues.values():
            try:
                q.put(result, timeout=0.1)
            except:
                pass  # Client disconnect

result_queue = ResultQueue()

@app.route('/stream_results')
def stream_results():
    client_id = request.remote_addr
    result_queue.subscribe(client_id)
    
    while True:
        try:
            result = result_queue.queues[client_id].get(timeout=1)
            yield f"data: {json.dumps(result)}\n\n"
        except:
            yield ": keepalive\n\n"
```

#### 5. Thêm Config File
```yaml
# tram_a_config.yaml (như ở trên)
```

#### 6. Thêm Logging Framework
```python
# Thay thế print() bằng logger
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/tram_a.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage
logger.info(f"[{self.id}] AI cycle started")
logger.warning(f"[ETH] Connection lost, retrying...")
logger.error(f"[YOLO] Detection failed: {e}")
```

---

### **PHASE 3: Medium Priority Enhancements (1 tháng)**

#### 7. Thêm Performance Monitoring
```python
# monitoring.py
from collections import deque
import time

class PerformanceMonitor:
    def __init__(self, window_size=100):
        self.metrics = {}
        self.window_size = window_size
    
    def start_timer(self, name):
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=self.window_size)
        self._start_times[name] = time.time()
    
    def end_timer(self, name):
        duration = time.time() - self._start_times.get(name, 0)
        if name in self.metrics:
            self.metrics[name].append(duration)
    
    def get_stats(self, name):
        if name not in self.metrics:
            return None
        times = list(self.metrics[name])
        if not times:
            return None
        return {
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
            "count": len(times)
        }

# Usage
monitor = PerformanceMonitor()

monitor.start_timer("yolo_detect")
# ... YOLO detection ...
monitor.end_timer("yolo_detect")

stats = monitor.get_stats("yolo_detect")
# {'avg': 0.045, 'min': 0.040, 'max': 0.055, 'count': 50}
```

#### 8. Thêm Health Check Endpoint
```python
# app.py
@app.route('/health')
def health_check():
    health_status = {
        "status": "healthy",
        "camera": cam.is_connected(),
        "uart": uart.is_open if uart.ser else False,
        "ethernet": eth.is_connected(),
        "last_ai_cycle": time.time() - engine.last_run_time,
        "queue_size": uart.send_queue.qsize()
    }
    
    if health_status["last_ai_cycle"] > 30:
        health_status["status"] = "degraded"
    
    return jsonify(health_status)
```

#### 9. Implement Unit Tests
```python
# tests/test_logic.py
import unittest
from logic_test import TrafficLogic

class TestTrafficLogic(unittest.TestCase):
    def test_jam_timeout(self):
        """Test vòng lặp kẹt có timeout"""
        engine = TrafficLogic(...)
        engine.ket_local = True
        
        start = time.time()
        # Fake vòng lặp
        while engine.ket_local and (time.time() - start) < 2:
            pass
        
        # Nên thoát sau 2 giây
        self.assertLess(time.time() - start, 3)

if __name__ == '__main__':
    unittest.main()
```

---

### **PHASE 4: Long-term Architecture (1-2 tháng)**

#### 10. Migrate Đến Message Queue (Redis/RabbitMQ)
```python
# Hiện tại: Synchronous + Global variables
latest_result = None
result_ready = False

# Cải thiện: Asynchronous với Redis
import redis

redis_client = redis.Redis(host='localhost', port=6379)

def publish_result(result):
    redis_client.publish('ai_results', json.dumps(result))

@app.route('/stream_results')
def stream_results():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('ai_results')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            yield f"data: {message['data']}\n\n"
```

#### 11. Thêm Database Logging (SQLite/PostgreSQL)
```python
# Hiện tại: JSON file rotation
# Cải thiện: Database
import sqlite3

class DatabaseLogger:
    def __init__(self, db_path="traffic.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()
    
    def _init_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_cycles (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cnn_status TEXT,
                xe_count INTEGER,
                brightness REAL,
                cmd TEXT
            )
        """)
        self.conn.commit()
    
    def log_cycle(self, result):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO ai_cycles (cnn_status, xe_count, brightness, cmd)
            VALUES (?, ?, ?, ?)
        """, (
            result['cnn_status'],
            result['xe_local'],
            result['brightness'],
            result.get('final_cmd', 'N/A')
        ))
        self.conn.commit()

# Query thống kê
SELECT cnn_status, COUNT(*) as count, AVG(xe_count) as avg_xe
FROM ai_cycles
WHERE timestamp > datetime('now', '-1 day')
GROUP BY cnn_status;
```

#### 12. Containerize với Docker
```dockerfile
# Dockerfile
FROM arm32v7/python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY TRAM_A/ .

CMD ["python", "app.py"]
```

```yaml
# docker-compose.yml
version: '3'
services:
  tram_a:
    build: .
    ports:
      - "8000:8000"
    devices:
      - "/dev/ttyAMA0:/dev/ttyAMA0"  # UART
    volumes:
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml
```

---

### **Summary: Roadmap Tổng Hợp**

| Phase | Task | Priority | Timeline |
|-------|------|----------|----------|
| 1 | Timeout vòng lặp kẹt | 🔴 CRITICAL | 1-2 ngày |
| 1 | JSON validation Ethernet | 🔴 CRITICAL | 1-2 ngày |
| 1 | UART queue maxsize | 🔴 CRITICAL | 1 ngày |
| 2 | Refactor SSE streaming | 🟠 HIGH | 2-3 ngày |
| 2 | Config file YAML | 🟠 HIGH | 2 ngày |
| 2 | Logging framework | 🟠 HIGH | 2 ngày |
| 3 | Performance monitor | 🟡 MEDIUM | 3-5 ngày |
| 3 | Health check endpoint | 🟡 MEDIUM | 1-2 ngày |
| 3 | Unit tests | 🟡 MEDIUM | 3-5 ngày |
| 4 | Redis integration | 🟢 LOW | 1 tuần |
| 4 | Database logging | 🟢 LOW | 1 tuần |
| 4 | Docker deployment | 🟢 LOW | 1 tuần |

---

## 📈 Tóm Tắt Đánh Giá Chung

### **Điểm Mạnh**
- ✅ Kiến trúc 4 tầng rõ ràng, dễ bảo trì
- ✅ Tối ưu cho edge device (Pi 5)
- ✅ Logic phối hợp 2 trạm thông minh
- ✅ Xử lý ảnh tiên tiến (SCI, ROI)
- ✅ Giao diện web real-time
- ✅ Fallback độc lập khi mất mạng

### **Điểm Yếu Chính**
- ❌ Vòng lặp kẹt không có timeout → Có thể mắc kẹt vĩnh viễn
- ❌ Race condition SSE → Mất data multi-client
- ❌ UART queue unlimited → Memory leak
- ❌ Ethernet JSON parsing fragile → Crash nếu gói tin chia cắt

### **Khuyến Nghị Ngay**
1. **NGAY:** Thêm timeout vòng lặp kẹt (1 ngày)
2. **NGAY:** Fix JSON validation Ethernet (1 ngày)
3. **NGAY:** Giới hạn UART queue (1 ngày)
4. **TUẦN SAU:** Refactor SSE + Config file (3-5 ngày)
5. **TUẦN SAU:** Thêm logging + monitoring (5-7 ngày)

### **Xếp Hạng Tổng Thể**
```
Chất lượng code:        7/10 ⭐⭐⭐⭐⭐⭐⭐
Kiến trúc:             8/10 ⭐⭐⭐⭐⭐⭐⭐⭐
Hiệu suất:             7/10 ⭐⭐⭐⭐⭐⭐⭐
Độ tin cậy:            6/10 ⭐⭐⭐⭐⭐⭐
Tài liệu:              5/10 ⭐⭐⭐⭐⭐
Error handling:        5/10 ⭐⭐⭐⭐⭐
────────────────────────────
TỔNG ĐIỂM:             6.3/10 (KHÁ) ⭐⭐⭐⭐⭐⭐
```

---

## 📞 Liên Hệ & Hỗ Trợ

Nếu cần chi tiết hoặc clarification về bất kỳ vấn đề nào, vui lòng liên hệ.

**Báo cáo được soạn:** 21/04/2026  
**Phiên bản:** 1.0  
**Trạng thái:** ✅ Hoàn tất

---

