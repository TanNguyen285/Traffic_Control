# Traffic_Control System Overview

## 1. Mục tiêu dự án
- Hệ thống giám sát điều khiển giao thông bằng camera, AI và Raspberry Pi.
- Phát hiện, phân loại phương tiện, cảnh báo, lưu trữ dữ liệu và điều khiển hành vi.
- Hỗ trợ triển khai trên web (Flask) và trên Raspberry Pi (dịch vụ systemd).

## 2. Cấu trúc thư mục chính
- `app.py`, `camera.py`, `logic.py`, `pre_processor_image.py`, `yoloxx.py` (trong `web_test/`):
  - Ứng dụng web Flask cung cấp endpoint để nhận ảnh/camera, xử lý và trả kết quả.
  - `camera.py`: cấu hình video/camera.
  - `logic.py`: thuật toán điều khiển, cảnh báo luồng.
  - `pre_processor_image.py`: tiền xử lý ảnh đầu vào trước khi inference.
  - `yoloxx.py`: module YOLO (dự đoán vật thể).

- `static/` và `templates/` (`web_test/`): giao diện web, file CSS/JS, JSON kết quả.
- `Service_Pi5/`:
  - `yolo_flask.service`, `yolo_flask.sh`: dịch vụ để khởi chạy Flask trên Raspberry Pi 5.

- `runs/detect/`:
  - kết quả huấn luyện YOLO, trọng số `best.pt`, `last.pt`, và triển khai NCNN.

- `web_test/SCI/`, `web_test/SimpleCNN/`:
  - Mô hình CNN tùy chỉnh, dữ liệu và huấn luyện cho các tác vụ đặc thù.

- `Rasp_thongso.py`: script cấu hình tham số Raspberry.
- `ESP32.cpp`: mã cho phần cứng ESP32 (giao tiếp cảm biến/điều khiển).

## 3. Luồng dữ liệu chính
1. Camera hoặc ảnh được cung cấp qua API web.
2. Ảnh qua `pre_processor_image` -> chuẩn hóa, resize, tiền xử lý.
3. Inference YOLO qua `yoloxx` (đã huấn luyện trong `runs/detect/`) để phát hiện xe.
4. `logic` xử lý kết quả (đếm xe, phân loại, tốc độ, điều khiển đèn).
5. Kết quả trả về API, ghi `static/last_detection.json`, hiển thị trên UI.
6. Có thể kết nối đến phần cứng `ESP32` để điều khiển thực tế.

## 4. Triển khai
- Chạy Flask trong `web_test/app.py`.
- Trên Raspberry Pi, dùng `Service_Pi5/yolo_flask.service` để quản lý service.
- Kiểm tra endpoint, xem log và dữ liệu đầu ra trong thư mục `runs/` và `web_test/static/`.

## 5. Mở rộng và tối ưu
- Dùng `runs/detect/yolov26_epoch*` để cập nhật weights tốt nhất.
- Thêm chức năng phát hiện lỗi, cảnh báo va chạm, điều phối lưu lượng.
- Tích hợp tiếp vào dashboard, cơ chế lưu lịch sử, phân tích thống kê.

---

> Lưu ý: Nội dung mô tả dựa trên cấu trúc thư mục hiện tại và các file có trong repo. Nếu cần chi tiết từng module, có thể mở thêm file `web_test/logic.py`, `web_test/yoloxx.py` để bổ sung.