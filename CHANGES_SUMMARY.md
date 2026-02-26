# Traffic Control V1 - Update Summary

## Tóm Tắt Các Thay Đổi

### 1. **HTML Module** (`templates/index.html`)
- ✅ **Xóa thanh IOU & Confidence sliders** - Các thanh trượt đã bị xóa hoàn toàn
- ✅ **Thêm file upload control** - Người dùng có thể chọn ảnh từ máy tính qua `<input type="file">`
- ✅ **Fix class names** - Thay đổi từ 6 class mặc định thành đúng 4 class: `['bus', 'car', 'motorbike', 'truck']`
- ✅ **Xóa nút Download** - Loại bỏ nút tải ảnh kết quả
- ✅ **Giữ 2 nút chính**: "🚀 Detect" (upload) và "📷 Chụp ảnh" (camera)

### 2. **Backend** (`app.py`)
- ✅ **Upload endpoint** (`/upload_image`) - Lưu ảnh tạm thời vào `selected_image` (không lưu disk)
- ✅ **Detect endpoint** (`/camera_capture`) - Detect từ `selected_image` nếu có, không thì dùng camera
- ✅ **Base64 embedding** - Ảnh gốc và kết quả được encode thành base64 (không lưu file)
- ✅ **Sửa signature API** - `ai.detect(ready_frame, brightness)` (bỏ OUTPUT_DIR, STATIC_DIR)
- ✅ **Pass class_names to template** - Template nhận class names từ Flask route
- ✅ **JSON logging** - Ghi `last_detection.json` để polling (chỉ chứa counts, không ảnh)
- ✅ **Import json** - Thêm `import json` vào đầu file

### 3. **AI Detection Module** (`yoloxx.py`)
- ✅ **Signature đơn giản hóa** - `detect(processed_frame, brightness_val)` (xóa output_dir, static_dir)
- ✅ **Base64 image** - Trả ảnh detect dưới dạng base64: `processed_image: "data:image/jpeg;base64,..."`
- ✅ **Không lưu file** - Xóa logic `cv2.imwrite()` - ảnh chỉ được encode thành string
- ✅ **Trả về kết quả minimal** - Chỉ gồm `counts, total_vehicles, brightness, timestamp, processed_image`

### 4. **Frontend** (`static/script.js`)
- ✅ **Upload handler** - `uploadFileIfNeeded()` - gửi file lên `/upload_image` trước detect
- ✅ **Xóa slider listeners** - Bỏ hết code xử lý conf/iou sliders
- ✅ **Xóa download button logic** - Loại bỏ link download kết quả
- ✅ **Handle base64 images** - Nhận `input_image` và `processed_image` từ JSON, hiển thị trực tiếp
- ✅ **Clear file input** - Sau detect, reset file input để sử dụng camera lần sau
- ✅ **Camera button fix** - Bấm "📷 Chụp ảnh" sẽ xóa file upload và dùng camera
- ✅ **File name display** - Chỉ hiển thị tên file, không hiển thị kích thước hay tên output

### 5. **CSS** (`static/style.css`)
- ✅ **Thêm file-input styles** - Styling cho file input selector
- ✅ **Giữ button styles** - Detect và Camera buttons vẫn giữ design gốc

### 6. **Modules Không Thay Đổi** ✓
- ✅ `camera.py` - Logic camera thread-safe **vẫn không đổi**
- ✅ `pre_processor_image.py` - Logic xử lý ảnh (ROI, brightness, SCI) **vẫn không đổi**
- ✅ `uart_service.py` - Logic UART gửi lệnh **vẫn không đổi**

## Flow Xử Lý

### Scenario 1: Upload ảnh từ máy tính
```
1. User chọn ảnh → DOM shows file name
2. User bấm "Detect"
3. JS upload ảnh → `/upload_image`
4. Backend lưu vào `selected_image` (RAM)
5. JS gọi `/camera_capture`
6. Backend detect từ `selected_image`
7. Trả ảnh gốc + ảnh detect (base64)
8. UI hiển thị, file input reset
```

### Scenario 2: Chụp từ camera
```
1. User bấm "📷 Chụp ảnh"
2. File input được xóa
3. JS gọi `/camera_capture`
4. Backend detect từ camera
5. Trả ảnh gốc + ảnh detect (base64)
6. UI hiển thị
```

### Scenario 3: UART trigger
```
1. UART gửi signal
2. Backend gọi `perform_detection()` từ camera
3. Trả kết quả, ghi `last_detection.json`
4. JS polling phát hiện thay đổi
5. UI tự cập nhật (không hiển thị ảnh từ UART)
```

## Lợi Ích

✨ **Không lưu trữ disk**: Ảnh chỉ tồn tại trong RAM/base64
✨ **2 nút chính rõ ràng**: Upload hoặc Camera
✨ **4 class đúng**: bus, car, motorbike, truck
✨ **Giao diện sạch**: Bỏ slider confidence/iou không cần thiết
✨ **Logic rõ ràng**: Kết nối đúng giữa backend-frontend

---

**Ngày cập nhật**: 2026-02-26  
**Trạng thái**: ✅ Hoàn tất
