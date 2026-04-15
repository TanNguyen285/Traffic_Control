# 🚦 Traffic Control System  
## Edge AI-based Solution for Real-Time Traffic Management on Raspberry Pi 5
<img width="1248" height="884" alt="image" src="https://github.com/user-attachments/assets/abde69f0-382a-43bd-88bd-e903f0576164" />


---

## 🚀 Key Highlights

### 🌙 Low-Light   
Tích hợp **SCI** giúp hệ thống duy trì độ chính xác cao trong điều kiện ánh sáng yếu, ban đêm hoặc ngược sáng.

Source : 

      Github:https://github.com/vis-opt-group/SCI

### ⚡ High Performance  
YOLOv26n được tối ưu hóa trên **Raspberry Pi 5**, hệ thống đạt khả năng xử lý **thời gian thực** nhờ framework **NCNN**.

Source : 

      Github:https://github.com/Tencent/ncnn
### 🪶 Ultra-Lightweight  
Sử dụng kiến trúc **SimpleCNN** (*0.251M parameters*) cho phép phân tích mật độ giao thông hiệu quả mà không tiêu tốn nhiều tài nguyên.

---

## 🏗 System Architecture

Hệ thống được thiết kế theo **Sequential Pipeline gồm 4 tầng chính**:

### 1. 🖼 Image Pre-processing  
- Khử nhiễu và cân bằng ánh sáng  
- Sử dụng mạng **SCI (Weight Sharing)** để tối ưu hiệu suất xử lý
-
  <img width="1170" height="475" alt="image" src="https://github.com/user-attachments/assets/1dbff8be-24cc-4a61-981e-bbdc96e7cd4f" />

  



### 2. 📊 Density Analysis  
- Áp dụng **SimpleCNN** trên vùng ROI *(224x224)*  
- Đánh giá sơ bộ mức độ ùn tắc giao thông

  <img width="3444" height="1484" alt="image" src="https://github.com/user-attachments/assets/36e97e73-bbe5-4965-b50a-251ff20e6e1c" />


### 3. 🚗 Object Detection  
- Triển khai **YOLOv26n**   
- Nhận diện chính xác nhiều loại phương tiện

  <img width="999" height="374" alt="image" src="https://github.com/user-attachments/assets/8d301af1-876d-42d7-87b5-44b69dacf76f" />


### 4. 🚦 Control Logic  
- Điều phối đèn tín hiệu giao thông thông minh  

  <img width="575" height="813" alt="image" src="https://github.com/user-attachments/assets/bb658f17-e950-4e42-a7f9-4dd7def7e617" />


---

## 🧠 Tổng Quan

ITCS là một giải pháp **Edge AI hoàn chỉnh**, kết hợp giữa **xử lý ảnh nâng cao**, **phân tích mật độ**, và **nhận diện đối tượng** nhằm tối ưu hóa điều phối giao thông trong thời gian thực — đặc biệt phù hợp với các hệ thống nhúng chi phí thấp.

---
