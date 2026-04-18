# Hướng dẫn hệ thống Traffic_PC (Web Test)

## 1. Tổng quan

Hệ thống là một giải pháp giám sát giao thông với:
- Camera vật lý cấp dữ liệu (cv2 VideoCapture)
- YOLO object detection (Phiên bản Ultrayltics + NCNN weights)
- CNN classification (SimpleCNN) để phát hiện kẹt xe / thông thoáng
- SCI (low-light enhancement) model xử lý ảnh thiếu sáng
- Flask + webview giao diện frontend
- UART (tuỳ chọn) gửi lệnh điều khiển tín hiệu

Đầu vào: hình ảnh camera hoặc ảnh tĩnh upload.
Đầu ra: JSON chứa số xe, trạng thái giao thông, thời gian đèn màu, hình ảnh trả về Base64.

## 2. Cấu trúc file chính

- `app.py`: Core app + khởi tạo module + API endpoints + video stream + cửa sổ GUI
- `camera.py`: Quản lý luồng camera, tự reconnect, lấy frame ở background
- `logic.py`: TrafficLogic (quy trình xử lý + CNN + YOLO + điều kiện kẹt xe + UART)
- `tienxulyanh.py`: Tiền xử lý ảnh - ROI, brightness, SCI enhancement, dual frame (CNN + YOLO)
- `yoloxx.py`: Wrapper YOLO dùng `ultralytics.YOLO`, đếm class, xuất ảnh Base64
- `model_sci.py`: Mạng CNN SCI + Enhance/Calibrate + Finetunemodel
- `loss_sci.py`: Hàm mất mát dùng MSE + Smooth (yCbCr + gradient weight)
- `uart_service.py`: UART interface (Serial không bắt buộc), lắng nghe, transmit
- `SimpleCNN/`: custom model và dữ liệu cho phân loại hai nhãn

## 3. Sơ đồ cây cấu trúc (folder & module)

```
web_test/
├─ app.py
├─ camera.py
├─ logic.py
├─ tienxulyanh.py
├─ yoloxx.py
├─ uart_service.py
├─ model_sci.py
├─ loss_sci.py
├─ weights/ (medium.pt, easy.pt, difficult.pt)
├─ runs/
│  ├─ detect/yolov26_epoch50/weights/best_ncnn_model/*
│  └─ exp3/best_cnn_model.pth
├─ SimpleCNN/
│  ├─ custom.py
│  ├─ dataset_custom.py
│  └─ train_custom.py
├─ templates/index.html
├─ static/script.js
└─ static/style.css
```

## 4. Luồng xử lý chính trong `app.py`

1. `Camera(src=0)` khởi chạy background thread, đọc frame.
2. Tạo `Thread` chạy Flask local `127.0.0.1:8000`.
3. `pre_proc = Tienxulyanh(...)` và nạp SCI model nếu có.
4. `ai_yolo = Yolo_AI()` từ ultralytics + load weights NCNN.
5. `cnn_net = SimpleCNN(...)` load mô hình classification 2 class.
6. Khởi tạo `TrafficLogic` với các module cần thiết.
7. Các route:
   - `/` trả về UI HTML
   - `/detect_static` nhận file ảnh, gọi `engine.perform_detection(img)`
   - `/data_a` lấy frame từ camera, gọi `engine.perform_detection(frame)`
   - `/data_b` trả về giá trị tĩnh (demo)
   - `/video_feed` stream MJPEG camera

## 5. Luồng xử lý ảnh trong `TrafficLogic.perform_detection`

1. Xử lý ảnh dual trong `Tienxulyanh.process_dual`:
   - crop ROI (0.1-0.9 chiều dọc, 0-1 chiều ngang)
   - brightness
   - SCI enhancement nếu sáng thấp (<0.4)
   - resize 224x224 cho CNN, 640x640 (letterbox) cho YOLO
2. `predict_cnn(frame_cnn)` trả status = `Ket Xe`/`Thong Thoang` và conf
3. Nếu `Ket Xe`: giả định tình trạng kẹt xe, cmd `m4`, set total_vehicle kẹt xe, ghép hình ảnh với overlay text
4. Nếu `Thong Thoang`: gọi `ai_yolo.detect(frame_yolo, brightness)`
   - YOLO detect, class counts, total
   - convert output with bounding boxes sang Base64
   - tín hiệu đèn dựa total: <5 => m1 20s, <=10 => m2 45s, <=20 => m3 60s, >20 => m4 90s
5. Gửi lệnh UART: `uart.send(cmd)`
6. Trả về `result` + `cmd` cho API

## 6. Chạy hệ thống

1. Cài dependencies: `opencv-python`, `torch`, `ultralytics`, `flask`, `pywebview`, `numpy`, `pillow`, `torchvision`, `pyserial` (nếu UART)
2. Chạy:
   - `python app.py`
   - Mở cửa sổ GUI tự động với `webview`
3. Hoặc với web:
   - `curl --form "image=@/path/to/img.jpg" http://127.0.0.1:8000/detect_static`
   - `/data_a` xin dữ liệu streaming; `/video_feed` MJPEG

## 7. Ghi chú cho AI khác / phát triển

- Mô hình `runs/detect/yolov26_epoch50/weights/best_ncnn_model` là YOLO dạng NCNN (không trực tiếp PyTorch), nên cần cẩn thận nếu thay đổi.
- `SimpleCNN` chỉ 224x224, 2 class; dùng để chọn nhánh kẹt xe/thoáng.
- `Tienxulyanh` có ROI fix; có thể tinh chỉnh roi_box nếu camera khác.
- `uart_service.py` chỉ dummy trên Windows, dùng thực nơi Linux/RPI.
- `loss_sci.py` dùng .cuda() trong `SmoothLoss`, nên nếu chạy CPU cần sửa (current may break nếu ko GPU có / cuda không sẵn sàng).

## 8. Kiểm tra nhanh set-up

- Kiểm tra camera hoạt động: `python - <<EOF
from camera import Camera
c=Camera(0); c.start(); import time; time.sleep(3); print(c.read()[0]); c.stop();
EOF`
- Kiểm tra YOLO load: `python - <<EOF
from ultralytics import YOLO; y=YOLO('runs/detect/yolov26_epoch50/weights/best_ncnn_model'); print('ok')
EOF`

---

> File này vừa là tài liệu tham chiếu (kiến trúc + luồng data) vừa là sơ đồ cây hệ thống theo yêu cầu.
