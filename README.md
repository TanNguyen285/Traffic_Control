# 🚦 Traffic Control System  
## Edge AI-based Solution for Real-Time Traffic Management on Raspberry Pi 5
![Raspberry Pi5](IMAGE/ras.svg)


---

# 🚀 Key Highlights

## 🌙 Low-Light   
Tích hợp [**AI-SCI**](https://openaccess.thecvf.com/content/CVPR2022/html/Ma_Toward_Fast_Flexible_and_Robust_Low-Light_Image_Enhancement_CVPR_2022_paper.html) giúp hệ thống duy trì độ chính xác cao trong điều kiện ánh sáng yếu, ban đêm hoặc ngược sáng.

Source : 

      Github:https://github.com/vis-opt-group/SCI

## ⚡ High Performance  
YOLOv26n được tối ưu hóa trên Raspberry Pi 5, hệ thống đạt khả năng xử lý Real-Time nhờ framework [**NCNN**](https://docs.ultralytics.com/vi/integrations/ncnn/#key-features-of-ncnn-models)

Source : 

      Github:https://github.com/Tencent/ncnn
## 🪶 Ultra-Lightweight  
Sử dụng kiến trúc [**SimpleEfficientCNN**](https://www.mdpi.com/2077-0472/16/3/357) (*0.251M parameters*) cho phép phân tích mật độ giao thông hiệu quả mà không tiêu tốn nhiều tài nguyên.

---

# 🏗 System Architecture

Hệ thống được thiết kế theo **Sequential Pipeline gồm 4 tầng chính**:

## 1. 🖼 Image Pre-processing  
- Khử nhiễu và cân bằng ánh sáng  
- Sử dụng mạng **SCI (Weight Sharing)** để tối ưu hiệu suất xử lý
-
![alt text](IMAGE/sci.png)

  



## 2. 📊 Density Analysis  
- Áp dụng **SimpleCNN** trên vùng ROI *(224x224)*  
- Đánh giá sơ bộ mức độ ùn tắc giao thông

  <img width="8000" height="400" alt="image" src="https://github.com/user-attachments/assets/36e97e73-bbe5-4965-b50a-251ff20e6e1c" />


## 3. 🚗 Object Detection  
- Triển khai **YOLOv26n**   
- Nhận diện chính xác nhiều loại phương tiện

  <img width="999" height="374" alt="image" src="https://github.com/user-attachments/assets/8d301af1-876d-42d7-87b5-44b69dacf76f" />


## 4. 🚦 Control Logic  
- Điều phối đèn tín hiệu giao thông thông minh  
<table border="0">
  <tr>
    <td align="center">
      <img src="IMAGE/rasp_3d.png" alt="Raspberry Pi 3D" width="350"/>
      <br>
      <sub>Raspberry Pi Model</sub>
    </td>
    <td align="center">
      <img src="IMAGE/esp32_3d.png" alt="ESP32 3D" width="150"/>
      <br>
      <sub>ESP32 Module</sub>
    </td>
  </tr>
</table>

# 🧠 Tổng Quan

Traffic_Control là một giải pháp **Edge AI hoàn chỉnh**, kết hợp giữa **xử lý ảnh nâng cao**, **phân tích mật độ**, và **nhận diện đối tượng** nhằm tối ưu hóa điều phối giao thông trong thời gian thực — đặc biệt phù hợp với các hệ thống nhúng chi phí thấp.

---
