# Traffic_Control System - Chi Tiết Đầy Đủ

## 1. Mục tiêu dự án
- Hệ thống giám sát điều khiển giao thông thông minh bằng camera, AI, CNN và Raspberry Pi 5.
- Phát hiện & phân loại phương tiện (xe hơi, ô tô, xe máy, xe tải).
- Kiểm tra trạng thái giao thông (Thông thoáng / Kẹt xe).
- Điều khiển tín hiệu giao thông dựa trên mật độ phương tiện.
- Tích hợp UART gửi lệnh điều khiển đèn tới ESP32 (m1, m2, m3, m4).
- Giao diện web Flask hiển thị kết quả real-time.

---

## 2. Cấu trúc thư mục chính

### 2.1 Thư mục `web_test/` - Ứng dụng Flask chính
```
web_test/
├── app.py                 # Flask app, routes, khởi tạo tất cả models
├── camera.py             # Class Camera - quản lý luồng video
├── logic.py              # Class TrafficLogic - luồng xử lý chính
├── yoloxx.py            # Class Yolo_AI - inference YOLO
├── tienxulyanh.py       # Class Tienxulyanh - tiền xử lý ảnh
├── uart_service.py      # Class UARTService - giao tiếp UART
├── static/              # Tài nguyên tĩnh (CSS, JS, JSON)
│   ├── style.css        # Styling giao diện
│   ├── script.js        # Logic frontend
│   └── last_detection.json # Kết quả detection mới nhất
├── templates/           # HTML template
│   └── index.html       # Giao diện chính
├── SimpleCNN/           # Mô hình CNN phân loại trạng thái giao thông
│   ├── custom.py        # Class SimpleCNN - kiến trúc mô hình
│   ├── train_custom.py  # Script huấn luyện
│   └── dataset_custom.py # Xử lý dataset
└── SCI/                 # Mô hình cải thiện ảnh trong điều kiện tối
    ├── model_sci.py     # SCI Network - cải thiện khả năng chiếu sáng
    └── loss_sci.py      # Loss function cho SCI
```

### 2.2 Thư mục `runs/detect/` - Kết quả huấn luyện YOLO
```
runs/detect/
├── yolov26_epoch30/      # Phiên bản YOLO epoch 30
│   ├── weights/
│   │   ├── best.pt       # Trọng số tốt nhất (epoch 30)
│   │   └── best_ncnn_model/  # Model NCNN (tối ưu hóa tiềm tàng)
│   └── results.csv       # Kết quả huấn luyện
└── yolov26_epoch50/      # Phiên bản YOLO epoch 50 (sử dụng hiện tại)
    ├── weights/
    │   ├── best.pt       # Trọng số tốt nhất (epoch 50)
    │   └── best_ncnn_model/  # Model NCNN cho Raspberry Pi
    └── results.csv       # Kết quả huấn luyện
```

### 2.3 Thư mục `Service_Pi5/` - Dịch vụ Raspberry Pi
```
Service_Pi5/
├── yolo_flask.service   # Systemd service file - tự động khởi động khi boot
└── yolo_flask.sh        # Script bash - chạy Flask app
```

---

## 3. Chi Tiết Các Module Chính

### 3.1 📷 **camera.py** - Camera Module
```python
class Camera:
    def __init__(self, src=0, reconnect_interval=5.0, max_fail=20)
```
**Chức năng:**
- Quản lý luồng video từ webcam hoặc USB camera.
- Tự động kết nối lại nếu camera bị ngắt (mặc định sau 5s).
- Chạy trong thread riêng (threading) để không block chương trình chính.
- Hỗ trợ cả Windows (MSMF, DSHOW) và Linux (v4l2)/Raspberry Pi.

**Phương thức chính:**
- `start()`: Khởi động thread đọc frame liên tục.
- `read()`: Lấy frame hiện tại từ bộ đệm an toàn (thread-safe).
- `stop()`: Dừng luồng đọc và giải phóng tài nguyên.

**Ứng dụng:** Cung cấp livestream camera `/camera_stream` cho web, hoặc làm source cho `logic.py`.

---

### 3.2 🖼️ **tienxulyanh.py** - Image Preprocessing (Tiền Xử Lý Ảnh)
```python
class Tienxulyanh:
    def __init__(self, target_size=(640, 640), use_sci=True)
```

**Chức năng chính:**
1. **Crop ROI (Region of Interest):** Cắt vùng ảnh cần thiết (tránh xử lý toàn bộ).
2. **Tính độ sáng (Brightness):** Sử dụng HSV, lấy kênh Value để đo độ sáng.
3. **SCI Enhancement (nếu tối):** Áp dụng mô hình SCI để cải thiện ảnh trong điều kiện ánh sáng thấp.
4. **Tạo 2 nhánh xử lý song song:**
   - **Nhánh CNN (224×224):** Resize đơn giản, chuẩn bị cho SimpleCNN.
   - **Nhánh YOLO (640×640):** Letterbox (giữ tỉ lệ), chuẩn bị cho YOLO.

**Phương thức chính:**
- `process_dual(frame, roi_box=[0.1, 0.9, 0.0, 1.0])`: 
  - Input: Frame đầu vào + ROI box [y_start, y_end, x_start, x_end] (chuẩn hóa 0-1).
  - Output: (frame_cnn, frame_yolo, brightness).
- `_apply_sci(frame)`: Sử dụng mô hình SCI để cải thiện ảnh tối.
- `letterbox(img, new_shape)`: Thay đổi kích thước giữ tỉ lệ, thêm padding.

**Ứng dụng:** Là bộ xử lý trung tâm, tất cả ảnh qua đây trước khi inference YOLO/CNN.

---

### 3.3 🤖 **yoloxx.py** - YOLO Detection Module
```python
class Yolo_AI:
    def __init__(self, model_obj, class_names)
```

**Chức năng:**
- Chạy inference YOLO để phát hiện phương tiện.
- Đếm số lượng phương tiện theo từng lớp (car, van, bus, motorcycle, truck).
- Vẽ bounding box lên ảnh và mã hóa thành base64 để gửi về web.

**Phương thức chính:**
- `detect(processed_frame, brightness_val)`:
  - Input: Frame 640×640 đã qua xử lý + độ sáng.
  - Output: `{"counts": [c0, c1, c2, c3, c4], "total_vehicles": N, "processed_image": "data:...", ...}`.
  - Thực hiện:
    1. Chạy `model.predict()` với confidence threshold = 0.3.
    2. Duyệt danh sách detect boxes, đếm theo class.
    3. Vẽ box lên frame gốc.
    4. Chuyển thành base64 để web hiển thị.

**Config:**
- Classes: `['car', 'van', 'bus', 'motorcycle', 'truck']` (5 loại).
- Model path: `runs/detect/yolov26_epoch50/weights/best_ncnn_model` (hoặc best.pt).

---

### 3.4 🛣️ **logic.py** - Traffic Logic Engine
```python
class TrafficLogic:
    def __init__(self, yolo_ai, cnn_model, cnn_transform, cnn_classes, device, pre_proc, uart, cam)
```

**Chức năng tổng hợp:**
- **Nơi duy nhất chứa luồng xử lý chính** của hệ thống.
- Quy định logic:
  - Bước 1: Lấy frame từ camera hoặc ảnh được upload.
  - Bước 2: Tiền xử lý (Tienxulyanh) → tạo 2 nhánh ảnh (224×224 & 640×640).
  - Bước 3: CNN kiểm tra trước ("Thông Thoáng" hay "Kẹt Xe"?).
  - Bước 4: CHIA NHÁNH LOGIC:
    - Nếu **Kẹt Xe**: Điều khiển đèn sung (m4 = 90s), không cần YOLO.
    - Nếu **Thông Thoáng**: Chạy YOLO đếm xe → tính toán thời gian đèn.
  - Bước 5: Tính thời gian xanh theo mật độ (signal logic).
  - Bước 6: Gửi lệnh điều khiển qua UART.

**Phương thức chính:**
- `perform_detection(selected_image=None)`:
  - Hàm main, trả về `(result_dict, control_command)`.
  - Ghi tất cả logic xử lý vào đây.

- `predict_cnn(frame_cnn_cv2)`:
  - Dự đoán CNN trạng thái ("Thông Thoáng" hoặc "Kẹt Xe").
  - Return: `(class_name, confidence%, class_idx)`.

- `calculate_signal(total)`:
  - Tính thời gian xanh dựa trên số xe:
    - `< 5 xe` → 20s xanh (m1).
    - `5-10 xe` → 45s xanh (m2).
    - `10-20 xe` → 60s xanh (m3).
    - `> 20 xe` → 90s xanh (m4).
  - Return: `(total_seconds, command)`.

**Kết quả trả về:**
```json
{
  "cnn_status": "Thong Thoang",
  "cnn_confidence": "95.25%",
  "counts": [5, 2, 1, 0, 3],      // [car, van, bus, motorcycle, truck]
  "total_vehicles": 11,
  "brightness": 0.65,
  "total_seconds": 60,
  "green_seconds": 57,
  "processed_image": "data:image/jpeg;base64,..."
}
```

---

### 3.5 🔌 **uart_service.py** - UART Communication
```python
class UARTService:
    def __init__(self, port="/dev/ttyAMA0", baudrate=115200)
```

**Chức năng:**
- Giao tiếp UART với ESP32 qua cổng serial.
- Gửi lệnh điều khiển: `m1`, `m2`, `m3`, `m4` (các mức thời gian xanh).
- Lắng nghe phản hồi từ ESP32 (ví dụ trigger "yell" để bắt đầu detect).

**Phương thức chính:**
- `send(msg)`: Gửi message qua UART (tự động thêm newline).
  
- `start_listening(trigger_callback)`:
  - Chạy trong thread riêng.
  - Khi nhận "yell", gọi callback (trigger detection).

**Port config:**
- Raspberry Pi: `/dev/ttyAMA0` (UART0).
- Windows: `COM3` hoặc `COM4` (tùy USB adapter).

---

### 3.6 🧠 **SimpleCNN/custom.py** - CNN Classification Network
```python
class SimpleCNN(nn.Module):
    def __init__(self, num_classes=2)
```

**Kiến trúc mô hình:**
1. **Stem (Layer 1):** Conv 3→32 ch, stride 2 (spatial reduction).
2. **Blocks (Layers 2-7):** 6 khối EfficientBlock (Inverted Residual):
   - Xen kẽ stride 1 (residual) và stride 2 (downsample).
   - Kênh: 32 → 64 → 128 → 256.
3. **Classifier (Layers 8-9):** AdaptiveAvgPool → Dropout → FC.

**EfficientBlock:**
- Pointwise Expansion (mở rộng kênh).
- Depthwise Conv (tích chập chiều sâu - hiệu quả).
- Pointwise Linear Projection (nén lại).
- Residual connection (stride=1 & in==out).

**Input/Output:**
- Input: 224×224 RGB image.
- Output: 2 logits (cho 2 lớp: "Thông Thoáng", "Kẹt Xe").

**Huấn luyện:**
- Model nằm tại: `runs/exp3/best_cnn_model.pth`.
- Dùng transforms chuẩn ImageNet: Resize, Normalize.

---

### 3.7 💡 **SCI/model_sci.py** - Scene-aware Low-light Enhancement
```python
class EnhanceNetwork(nn.Module)
class CalibrateNetwork(nn.Module)
```

**Chức năng:**
- Cải thiện chất lượng ảnh trong điều kiện ánh sáng thấp (ảnh tối).
- Giúp YOLO phát hiện tốt hơn khi ban đêm hoặc trong đường hầm.

**Cấu trúc:**
1. **EnhanceNetwork:** Điều chỉnh độ sáng tổng (tăng độ sáng).
2. **CalibrateNetwork:** Hiệu chỉnh màu sắc (giảm artifact).

**Áp dụng:**
- Gọi từ `tienxulyanh._apply_sci()` khi brightness < 0.4.
- Input: RGB tensor.
- Output: Enhanced RGB tensor (0-1 range).

---

## 4. chi tiết giao diện web (HTML/JS/CSS)

### 4.1 📄 **templates/index.html** - Cấu trúc trang
```
HEADER
├── Tiêu đề: "🔍 YOLOv8 Object Detection"
└── Status panel (YOLOv8 Demo)

MAIN CONTAINER
├── ROW 1: Input & Camera Live
│   ├── LEFT: File input, Detect button, Camera Capture button
│   └── RIGHT: Live camera stream
│
├── ROW 2: Image display
│   ├── Original Image (input)
│   └── Processed Image (output with detections)
│
└── ROW 3: Configuration & Statistics
    ├── LEFT: Traffic lights + Density
    │   ├── 🚦 3 đèn (Xanh/Vàng/Đỏ) + thời gian
    │   ├── Total vehicles count
    │   └── Density level (🟢 Ít / 🟡 TB / 🟠 Khá / 🔴 Đông)
    │
    └── RIGHT: Vehicle count by class
        └── 5 hộp đếm [car, van, bus, motorcycle, truck]

FOOTER
└── Credits
```

### 4.2 🎨 **static/style.css** - Styling
**Chủ đề:** Dark modern (background xanh đêm).

**Các phần chính:**
1. **Header:** Gradient `#16213e` → `#0f3460`, gradient text title.
2. **Control Panel:** Dark box với border cyan, transition smooth.
3. **Traffic Light Panel:**
   - 3 đèn tròn (48px) với màu: Xanh (#00ff00), Vàng (#ffff00), Đỏ (#ff0000).
   - Active state: full opacity + glow shadow.
   - Inactive: opacity thấp.
4. **Image Box:** Container fullwidth với border, hiểu thị ảnh responsive.
5. **Count Grid:** 5 hộp grid, dễ đọc.
6. **Loading Indicator:** Spinner animation + text overlay.

---

### 4.3 🎯 **static/script.js** - Frontend Logic
```javascript
// ========== MAIN FLOW ==========
1. DOMContentLoaded
   ├── startCamera()           // Hiển thị livestream
   └── startLastDetectionPolling()

2. User Click "🚀 Detect"
   ├── uploadFileIfNeeded()    // Upload ảnh nếu chọn
   ├── fetch POST /camera_capture
   └── handleCaptureResponse() // Cập nhật UI

3. User Click "📷 Chụp ảnh"
   └── Tương tự flow Detect
```

**Hàm chính:**

| Hàm | Chức năng |
|-----|----------|
| `startTimer()` | Bắt đầu đếm thời gian xử lý (00:00:00 format). |
| `uiStart()` | Hiển thị loading, disable nút. |
| `uiEnd()` | Ẩn loading, enable nút. |
| `updateDensity(count)` | Cập nhật tổng xe & mức độ (🟢/🟡/🟠/🔴). |
| `updateLightTimes(g, y, r)` | Cập nhật thời gian 3 đèn. |
| `showProcessedImage(url)` | Hiển thị ảnh đã xử lý. |
| `handleCaptureResponse(data)` | Cập nhật toàn bộ UI từ JSON response. |
| `captureFrameAndSend()` | Gửi request POST /camera_capture. |

**Flow xử lý response:**
```json
Input Response:
{
  "counts": [5, 2, 1, 0, 3],
  "total_vehicles": 11,
  "processed_image": "data:image/jpeg;...",
  "green_seconds": 57,
  "yellow_seconds": 3,
  "total_seconds": 60
}

Cập nhật UI:
1. count-0, count-1, ... → counts[0], counts[1], ...
2. totalVehicles → tổng số
3. densityLevel → 🟢/🟡/🟠/🔴
4. processedImg.src → hiển thị ảnh
5. greenTime, yellowTime, redTime → cập nhật thời gian
```

---

## 5. **app.py** - Flask Application Main

### 5.1 Khởi tạo các module
```python
cam = Camera(src=0)                          # Webcam #0
uart = UARTService(port="COM3")              # Serial port
pre_proc = Tienxulyanh(target_size=(640, 640), use_sci=True)

# Load YOLO model
yolo_model = YOLO("runs/detect/yolov26_epoch50/weights/best_ncnn_model")
ai_yolo = Yolo_AI(yolo_model, class_names=['car', 'van', 'bus', 'motorcycle', 'truck'])

# Load CNN model
cnn_net = SimpleCNN(num_classes=2).to(device)
cnn_net.load_state_dict(torch.load("runs/exp3/best_cnn_model.pth", ...))

# Khởi tạo TrafficLogic (engine chính)
engine = TrafficLogic(ai_yolo, cnn_net, cnn_transform, ...)
```

### 5.2 Routes chính
| Route | Method | Chức năng |
|-------|--------|----------|
| `/` | GET | Trả HTML index.html. |
| `/camera_capture` | POST | Gọi `engine.perform_detection()`, return JSON. |
| `/upload_image` | POST | Upload ảnh từ form, lưu vào `selected_image`. |
| `/camera_stream` | GET | MJPEG stream từ camera (multipart/x-mixed-replace). |

---

## 6. Luồng dữ liệu tổng quát (End-to-End)

```
📷 Người dùng chọn ảnh hoặc bấm "Chụp ảnh"
    ↓
🌐 Frontend (JS) gửi POST /camera_capture
    ↓
🖇️ app.py nhận request, gọi engine.perform_detection()
    ↓
📌 logic.py (TrafficLogic):
    1. Lấy frame từ camera (hoặc selected_image)
    ↓
🖼️ tienxulyanh.py:
    2. Tính độ sáng → Crop ROI → Apply SCI (nếu tối)
    3. Tạo 2 nhánh: frame_cnn (224×224) & frame_yolo (640×640)
    ↓
🧠 SimpleCNN:
    4. Dự đoán CNN: "Thông Thoáng" hay "Kẹt Xe"?
    ↓
❓ logic.py (CHIA NHÁNH):
    ┌─→ Nếu "Kẹt Xe": Đèn m4 (90s), STOP
    └─→ Nếu "Thông Thoáng":
        ↓
        🤖 yoloxx.py (YOLO):
        5. Phát hiện xe → Đếm theo 5 lớp
        ↓
        📊 logic.py (calculate_signal):
        6. Tính thời gian xanh từ số xe (m1/m2/m3/m4)
        ↓
        🔌 uart_service.py:
        7. Gửi lệnh điều khiển qua UART → ESP32
        ↓
        🎨 yoloxx.py:
        8. Vẽ box xe, chuyển thành base64

    ↓
📤 logic.py trả về JSON kết quả:
    {
      "cnn_status": "Thong Thoang",
      "counts": [5, 2, 1, 0, 3],
      "total_vehicles": 11,
      "processed_image": "data:...",
      "green_seconds": 57,
      "total_seconds": 60,
      ...
    }
    ↓
💾 app.py ghi kết quả → static/last_detection.json
    ↓
🌐 Frontend JS nhận JSON, cập nhật UI:
    - Hiển thị ảnh detect
    - Học kết quả đèn (xanh, vàng, đỏ)
    - Hiển thị mật độ giao thông
    - Cập nhật thời gian đếm ngược

✅ Hoàn tất
```

---

## 7. Các tính năng nâng cao

### 7.1 SCI (Scene-aware Low-light Enhancement)
- **Khi nào dùng:** `brightness < 0.4` (ảnh tối).
- **Cách dùng:** `tienxulyanh._apply_sci(frame)`.
- **Lợi ích:** Giúp YOLO phát hiện tốt hơn ở ban đêm.

### 7.2 ROI (Region of Interest)
- **Mục đích:** Chỉ xử lý vùng đường cần thiết (giảm tính toán).
- **Cách dùng:** `tienxulyanh.process_dual(frame, roi_box=[0.1, 0.9, 0.0, 1.0])`.
- **roi_box:** `[y_start, y_end, x_start, x_end]` chuẩn hóa 0-1.

### 7.3 Dual Pipeline
- **Frame CNN (224×224):** Nhanh, phân loại trạng thái.
- **Frame YOLO (640×640):** Chính xác hơn, phát hiện chi tiết.
- **Tối ưu:** Xử lý song song, tiết kiệm bandwidth.

### 7.4 Chia nhánh logic (Logic Branching)
- Nếu **Kẹt xe** → SKIP YOLO (nhanh hơn).
- Nếu **Thông thoáng** → Chạy YOLO để tối ưu tín hiệu.

---

## 8. Triển khai trên Raspberry Pi 5

### 8.1 Setup dịch vụ
```bash
# Copy file service
sudo cp Service_Pi5/yolo_flask.service /etc/systemd/system/

# Enable service
sudo systemctl enable yolo_flask
sudo systemctl start yolo_flask

# Kiểm tra log
sudo journalctl -u yolo_flask -f
```

### 8.2 Port & Config
- Flask chạy trên: `0.0.0.0:8000`.
- UART: `/dev/ttyAMA0` (Raspberry Pi default).
- Camera: `/dev/video0` (USB camera) hoặc Raspberry Pi Camera Module.

---

## 9. API Endpoints Tóm tắt

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/` | GET | - | HTML trang chủ |
| `/camera_capture` | POST | - | JSON kết quả detection |
| `/upload_image` | POST | file (form-data) | `{"success": true}` |
| `/camera_stream` | GET | - | MJPEG stream |

---

## 10. Cấu hình & Tuning

### 10.1 YOLO confidence threshold
```python
# yoloxx.py line 18
results = self.model.predict(processed_frame, conf=0.3)  # Giảm → looser, Tăng → stricter
```

### 10.2 Signal timing logic
```python
# logic.py - calculate_signal()
< 5   → m1 (20s)
5-10  → m2 (45s)
10-20 → m3 (60s)
> 20  → m4 (90s)
```
Thay đổi thresholds để phù hợp với giao thông thực tế.

### 10.3 SCI threshold
```python
# tienxulyanh.py line 39
if self.use_sci and self.brightness < 0.4:  # Điểu chỉnh 0.4 (40%)
```

---

## 11. Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-----------|----------|
| YOLO không phát hiện | Conf threshold quá cao | Giảm `conf` parameter. |
| ảnh tối | Licht thấp | Enable SCI, check `brightness < 0.4`. |
| Không có UART | Port sai | Check `UARTService(port="...")`. |
| Camera lag | FPS thấp | Giảm resolution hoặc cache frame. |

---

## 12. Lưu ý & Mở rộng

✅ **Hiện tại:**
- YOLO epoch 50 cho phát hiện xe.
- SimpleCNN phân loại "Thông Thoáng/Kẹt Xe".
- SCI cải thiện ảnh tối.
- UART điều khiển đèn giao thông.

🔄 **Có thể mở rộng:**
- Thêm object tracking (giám sát xe cụ thể).
- Phân tích vận tốc xe.
- Cảnh báo va chạm.
- Lưu trữ video & analytics.
- Dashboard thống kê chi tiết.
- Multi-lane support (nhiều làn đường).

---

> **Tài liệu này mô tả hệ thống Traffic Control hoàn chỉnh, từ phần cứng (camera, UART, ESP32) đến phần mềm (Flask, YOLO, CNN, SCI) và giao diện web (HTML/JS/CSS).**