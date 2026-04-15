# 🚦 ITCS: Intelligent Traffic Control System  
## Edge AI-based Solution for Real-Time Traffic Management on Raspberry Pi 5

---

## 🚀 Key Highlights

### 🌙 Low-Light   
Tích hợp **SCI** giúp hệ thống duy trì độ chính xác cao trong điều kiện ánh sáng yếu, ban đêm hoặc ngược sáng.

### ⚡ High Performance  
Được tối ưu hóa trên **Raspberry Pi 5**, hệ thống đạt khả năng xử lý **thời gian thực** nhờ framework **NCNN**.

### 🪶 Ultra-Lightweight  
Sử dụng kiến trúc **SimpleCNN** (*0.251M parameters*) cho phép phân tích mật độ giao thông hiệu quả mà không tiêu tốn nhiều tài nguyên.

---

## 🏗 System Architecture

Hệ thống được thiết kế theo **Sequential Pipeline gồm 4 tầng chính**:

### 1. 🖼 Image Pre-processing  
- Khử nhiễu và cân bằng ánh sáng  
- Sử dụng mạng **SCI (Weight Sharing)** để tối ưu hiệu suất xử lý

### 2. 📊 Density Analysis  
- Áp dụng **SimpleCNN** trên vùng ROI *(224x224)*  
- Đánh giá sơ bộ mức độ ùn tắc giao thông

### 3. 🚗 Object Detection  
- Triển khai **YOLOv8n** (đã tinh chỉnh)  
- Cấu hình:
  - SGD Momentum: **0.937**  
  - Loại bỏ **DFL (Distribution Focal Loss)**  
- Nhận diện chính xác nhiều loại phương tiện

### 4. 🚦 Control Logic  
- Điều phối đèn tín hiệu giao thông thông minh  
- Hỗ trợ **4 chế độ vận hành**:
  - Auto  
  - Manual  
  - (Có thể mở rộng thêm theo nhu cầu hệ thống)

---

## 🧠 Tổng Quan

ITCS là một giải pháp **Edge AI hoàn chỉnh**, kết hợp giữa **xử lý ảnh nâng cao**, **phân tích mật độ**, và **nhận diện đối tượng** nhằm tối ưu hóa điều phối giao thông trong thời gian thực — đặc biệt phù hợp với các hệ thống nhúng chi phí thấp.

---
