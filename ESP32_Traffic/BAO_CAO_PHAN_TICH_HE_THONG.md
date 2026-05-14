# BÁOCÁO PHÂN TÍCH HỆ THỐNG ĐIỀU KHIỂN ĐÈN GIAO THÔNG

**Ngày lập báo cáo:** 23/04/2026

---

## 1. TỔNG QUAN HỆ THỐNG

### 1.1 Mô Tả Chung
Đây là hệ thống điều khiển đèn giao thông tự động, được xây dựng trên vi điều khiển **ESP32** (DOIT DevKit v1) với khả năng giao tiếp với **Raspberry Pi** qua cổng UART. Hệ thống quản lý 2 ngã giao thông (Node A và Node B) với khả năng ưu tiên xả kẹt thông minh.

### 1.2 Thành Phần Chính
- **Vi điều khiển:** ESP32 DOIT DevKit v1
- **Giao tiếp:** UART 115200 baud với Raspberry Pi
- **Phần cứng điều khiển:** 3 đèn LED (Xanh/Vàng/Đỏ) cho mỗi node
- **Màn hình hiển thị:** 7-segment LED (MAX7219) hiển thị thời gian đếm ngược
- **Nút nhấn:** Nút khởi động thủ công
- **Cấu hình Node:** GPIO để xác định Node A hoặc Node B

### 1.3 Phiên Bản Firmware
- Framework: Arduino
- RTOS: FreeRTOS (tích hợp sẵn trong ESP32)
- Port theo dõi: COM5 @ 115200 baud

---

## 2. CÁCH HỆ THỐNG CHẠY

### 2.1 Kiến Trúc Phần Mềm

#### 2.1.1 Nhiệm Vụ (Tasks) FreeRTOS

Hệ thống sử dụng 2 task chạy song song:

**Task 1: `Doc_UART` (Core 0, Ưu tiên cao)**
- Chạy mỗi 5ms
- Liên tục đọc dữ liệu từ UART
- Phân giải các lệnh nhận được
- Đẩy lệnh vào hàng đợi (`FreeRTOS Queue`)
- Nhiệm vụ: Đảm bảo không bỏ mất dữ liệu từ Pi

**Task 2: `XuLyCapNhat` (Core 1, Ưu tiên thấp)**
- Chạy mỗi 10ms (độ phân giải 10ms)
- Lấy các lệnh từ hàng đợi
- Cập nhật trạng thái máy trạng thái (State Machine)
- Điều khiển đèn LED theo trạng thái hiện tại
- Cập nhật màn hình 7-segment

#### 2.1.2 Giao Tiếp Giữa Hai Task
- Sử dụng **FreeRTOS Queue** (kích thước 10 lệnh tối đa)
- Không dùng Mutex/Semaphore để giảm độ trễ
- Task 1 sản xuất lệnh, Task 2 tiêu thụ lệnh

---

### 2.2 Máy Trạng Thái (State Machine)

Hệ thống có **7 trạng thái chính:**

```
┌─────────────────────────────────────────────────────────┐
│                   CÁC TRẠNG THÁI                        │
└─────────────────────────────────────────────────────────┘

1. CHO_KHOI_DONG (Chờ khởi động)
   └─ Chờ nhấn nút START
   └─ Đèn tắt, màn hình xóa
   └─ Nút được debounce 30ms
   └─> Sang GREEN

2. GREEN (Đèn xanh)
   └─ Thời gian tùy mode (30s, 40s, 50s, 60s hoặc 90s)
   └─ Hiển thị thời gian đếm ngược
   └─ Gửi "run" tới Pi khi hết thời gian
   └─> Sang YELLOW

3. YELLOW (Đèn vàng)
   └─ Thời gian cố định: 5 giây
   └─ Hiển thị đếm ngược
   └─> Sang RED

4. RED (Đèn đỏ)
   └─ Thời gian = thời gian xanh + vàng (35s, 45s, 55s, 65s hoặc 95s)
   └─ Node kia bật đèn xanh
   └─> Quay lại GREEN

5. UU_TIEN (Xả kẹt - ưu tiên)
   └─ Chỉ một node được kích hoạt từ Pi
   └─ Đèn xanh bật liên tục (không đếm ngược)
   └─ Tối đa 150 giây
   └─ Thoát khi: nhận lệnh dừng hoặc timeout
   └─> Sang VANG_DEM

6. VANG_DEM (Vàng đệm - sau xả kẹt)
   └─ Đèn vàng 5 giây (chu kỳ quy chuẩn)
   └─> Sang CHO_MODE_MOI

7. CHO_MODE_MOI (Chờ mode mới)
   └─ Đã gửi "run" cho Pi
   └─ Chờ Pi phản hồi mode mới
   └─ Nếu timeout 20s → quay lại GREEN

8. EP_DO (Bị ép đỏ - khi node kia xả kẹt)
   └─ Đèn đỏ bắt buộc
   └─ Chờ lệnh từ node xả kẹt
   └─ Không tự động thoát
```

---

### 2.3 Các Loại Lệnh Từ Raspberry Pi

Hệ thống nhận 3 loại lệnh qua UART:

| Lệnh | Ý Nghĩa | Ví Dụ |
|------|---------|-------|
| `m0` - `m4` | Cập nhật mode/chu kỳ xanh | m0=30s, m1=40s, m2=50s, m3=60s, m4=90s |
| `A` hoặc `B` | Kích hoạt xả kẹt cho Node A/B | A = Node A xả kẹt |
| `a` hoặc `b` | Dừng xả kẹt cho Node A/B | a = Node A dừng xả kẹt |

---

### 2.4 Chu Kỳ Hoạt Động Bình Thường

```
GREEN (mode) ──10ms──> YELLOW (5s) ──10ms──> RED (mode+5s) ──10ms──> [lặp]
                          ▲
                          │ gửi "run" → Pi
                          │ nhận mode mới từ Pi
                          └─ CHO_MODE_MOI → GREEN
```

---

### 2.5 Chu Kỳ Xả Kẹt (Priority Mode)

```
GREEN (bình thường)
    ▼
Nhận lệnh 'A' từ Pi
    ▼
UU_TIEN (xanh liên tục, tối đa 150s)
    ▼ (nhận 'a' hoặc timeout)
VANG_DEM (5s, vàng tiêu chuẩn)
    ▼
CHO_MODE_MOI (gửi "run", chờ Pi)
    ▼
GREEN (chu kỳ mới bắt đầu)
```

---

### 2.6 Cấu Trúc Dữ Liệu

**Các Trạng Thái:**
```cpp
enum TrangThai {
    CHO_KHOI_DONG,  // Chờ khởi động
    GREEN,          // Xanh
    YELLOW,         // Vàng
    RED,            // Đỏ
    UU_TIEN,        // Xả kẹt
    VANG_DEM,       // Vàng sau xả kẹt
    EP_DO,          // Bị ép đỏ
    CHO_MODE_MOI    // Chờ mode mới
};
```

**Node ID (đọc từ GPIO4 lúc khởi động):**
```cpp
- GPIO4 = LOW  → Node A (bắt đầu XANH)
- GPIO4 = HIGH → Node B (bắt đầu ĐỎ)
```

---

## 3. ƯU ĐIỂM CỦA HỆ THỐNG

### 3.1 Kiến Trúc Phần Mềm
✅ **FreeRTOS Multitasking:** 
- Sử dụng 2 core của ESP32 hiệu quả
- Task đọc UART độc lập với task xử lý logic
- Tránh bỏ mất dữ liệu từ Raspberry Pi
- Giảm độ trễ phản ứng

✅ **Queue-based Communication:**
- Không dùng shared memory/Mutex → không deadlock
- Lệnh được xử lý tuần tự, an toàn
- Dễ scale-up nếu cần thêm task

✅ **Debounce Nút Nhấn (30ms):**
- Tránh nhiễu cơ học từ nút nhấn
- Phát hiện chính xác nhấn nút

✅ **Độ Phân Giải 10ms:**
- Đủ chính xác để điều khiển đèn giao thông
- Tiêu thụ năng lượng thấp so với 1ms

---

### 3.2 Chức Năng Điều Khiển

✅ **Xả Kẹt Thông Minh (Priority Mode):**
- Cho phép một node xả kẹt liên tục (150s tối đa)
- Node kia tự động chuyển sang RED (bị ép đỏ)
- Giảm tắc nghẽn ở ngã giao thông bị kẹt

✅ **Giao Tiếp Hai Chiều với Pi:**
- Nhận lệnh điều khiển từ Pi (mode, xả kẹt)
- Gửi "run" signal khi hết chu kỳ xanh
- Pi có thể theo dõi và điều chỉnh thời gian thực

✅ **Mode Chu Kỳ Linh Hoạt:**
- 5 mode khác nhau (m0-m4): 30s, 40s, 50s, 60s, 90s
- Pi có thể thay đổi mode mà không cần restart
- Thích ứng với lưu lượng giao thông

✅ **Cấu Hình Node Tự Động:**
- GPIO4 xác định Node A hay B tự động
- Node A ưu tiên xanh, Node B ưu tiên đỏ
- Sạch lắp ráp không cần jumper

---

### 3.3 Hiển Thị & Giám Sát

✅ **7-Segment LED Display:**
- Hiển thị thời gian đếm ngược rõ ràng
- Người dân biết còn bao lâu chờ đèn

✅ **Serial Debug Output (115200 baud):**
- Log chi tiết trạng thái hệ thống
- Dễ dàng debug khi phát triển

✅ **Đèn Xanh/Vàng/Đỏ Chuẩn:**
- Tuân thủ luật giao thông
- 2 đèn mỗi lần để tránh nhầm lẫn

---

### 3.4 Độ Tin Cậy

✅ **Khởi Tạo An Toàn:**
- Kiểm tra Queue tạo thành công trước khi chạy
- Nếu thất bại → restart lại

✅ **Xử Lý Timeout:**
- Xả kẹt timeout 150s → tự động thoát
- Mode mới timeout 20s → quay lại GREEN
- Không để hệ thống bị treo

✅ **Không Dùng Heap Động:**
- Tất cả object khởi tạo tĩnh (`static`)
- Tránh memory leak

---

## 4. NHƯỢC ĐIỂM CỦA HỆ THỐNG

### 4.1 Giao Tiếp & Đồng Bộ

❌ **Phụ Thuộc Vào Raspberry Pi:**
- Nếu Pi ngừng hoạt động, hệ thống vẫn chạy nhưng ở mode cố định
- Không thể tự động thích ứng lưu lượng giao thông

❌ **UART Không Đáng Tin Cậy:**
- Nếu dây cáp bị nhiễu, có thể mất lệnh
- Không có cơ chế checksum/CRC để phát hiện lỗi
- Baud rate cố định 115200 (không thí nghiệm tốc độ khác)

❌ **Không Có Handshaking:**
- Pi gửi lệnh nhưng không biết ESP32 có nhận được hay không
- Nếu queue đầy, lệnh bị bỏ mà Pi không biết

❌ **Độ Trễ Không Đảm Bảo:**
- Task xử lý chạy 10ms, không thực thời (hard real-time)
- Có thể bỏ sót frame UART nếu cùng lúc xử lý logic phức tạp

---

### 4.2 Chức Năng Điều Khiển

❌ **Xả Kẹt Chỉ Cho Một Node:**
- Không hỗ trợ xả kẹt cùng lúc hai node
- Trong trường hợp cả hai hướng đều kẹt, Pi phải quản lý ưu tiên

❌ **Không Phát Hiện Kẹt Tự Động:**
- Chỉ xả kẹt khi Pi gửi lệnh
- Pi phải có sensor/camera phát hiện kẹt

❌ **Timeout Cố Định:**
- Xả kẹt tối đa 150s (không cấu hình được)
- Mode chờ tối đa 20s (hardcoded)
- Thay đổi cần lập trình lại

❌ **Giới Hạn 5 Mode:**
- Chỉ 5 chu kỳ xanh định sẵn (30, 40, 50, 60, 90s)
- Không thể set thời gian tùy ý (e.g., 35s, 75s)

---

### 4.3 Độ Tin Cậy & Lỗi

❌ **Không Có Watchdog:**
- Nếu task bị deadlock, hệ thống không tự restart
- Cần watchdog I2C/SPI từ bên ngoài

❌ **Debounce Cố Định:**
- 30ms debounce có thể không đủ cho nút nhấn kém chất lượng
- Không cấu hình được

❌ **Không Ghi Log Vào Flash:**
- Chỉ in ra Serial, không lưu lịch sử lỗi
- Debug phức tạp khi ESP32 được đặt xa phòng kiểm soát

❌ **Lỗi GPIO:**
- Nếu GPIO4 nhiễu, node ID có thể bị đọc sai
- Không có cơ chế xác nhận node ID

---

### 4.4 Khả Năng Mở Rộng

❌ **Thiết Kế Cứng Cho 2 Node:**
- Khó thêm node thứ 3 hoặc 4
- Cần thiết kế lại máy trạng thái

❌ **Không Hỗ Trợ Cảm Biến Phụ:**
- Chỉ nút khởi động, không có sensor phát hiện xe
- Không thể làm tín hiệu đèn đỏ kéo dài khi có xe

❌ **Hiển Thị Giới Hạn:**
- 7-segment chỉ hiển thị 1 số, không thể show nhiều thông tin
- Không có LCD màn hình để hiển thị mode, node ID, lỗi

❌ **Lưu Trữ Cấu Hình:**
- Tất cả mode, timeout hardcoded trong firmware
- Không thể thay đổi cấu hình mà không flash lại

---

### 4.5 Hiệu Suất

❌ **Sử Dụng Tài Nguyên:**
- Chạy 2 task + queue → tiêu thụ RAM (bộ nhớ ổn nhưng không lý tưởng)
- FreeRTOS context switching mỗi 10ms có overhead

❌ **Queue Nhỏ (10 lệnh):**
- Nếu Pi gửi nhanh hơn 10 lệnh/100ms, queue sẽ bị tràn
- Lệnh bị bỏ, cần gửi lại

❌ **Không Có Prioritization Lệnh:**
- Lệnh xử lý tuần tự theo thứ tự FIFO
- Lệnh dừng xả kẹt không được ưu tiên

---

### 4.6 Bảo Mật & An Toàn

❌ **Không Mã Hóa UART:**
- Lệnh gửi qua UART không được bảo vệ
- Bất kỳ thiết bị nào kết nối UART cũng có thể gửi lệnh điều khiển

❌ **Không Xác Thực:**
- Không kiểm tra Pi gửi lệnh hay kẻ tấn công
- Không cơ chế token/signature

❌ **Không Xác Nhận Lệnh:**
- Pi gửi lệnh nhưng không nhận phản hồi xác nhận
- Không biết lệnh thành công hay thất bại

---

## 5. TÓMMTẮT SO SÁNH

| Khía Cạnh | Ưu Điểm | Nhược Điểm |
|-----------|---------|-----------|
| **Kiến Trúc** | FreeRTOS, 2-core, queue-based | Phụ thuộc Pi, không hard real-time |
| **Giao Tiếp** | UART 115200, 2-chiều | Không đáng tin, không checksum |
| **Mode** | 5 mode linh hoạt | Chỉ hardcoded, không tuỳ ý |
| **Xả Kẹt** | Hỗ trợ 150s, chuyển RED tự động | Chỉ 1 node, timeout cố định |
| **Node** | Tự động xác định qua GPIO | Thiết kế cứng cho 2 node |
| **Độ Tin Cậy** | Debounce, timeout, không heap động | Không watchdog, không log |
| **Hiển Thị** | 7-segment, serial debug rõ | Thông tin hạn chế |
| **Bảo Mật** | - | Không mã hóa, không xác thực |

---

## 6. KHUYẾN NGHỊ CẢI THIỆN

### Ngắn Hạn
1. ✅ Thêm CRC/checksum vào lệnh UART
2. ✅ Handshaking: ESP32 gửi ACK khi nhận lệnh
3. ✅ Cấu hình mode, timeout qua UART (không hardcoded)
4. ✅ Thêm watchdog SPI/I2C từ MCU riêng

### Trung Hạn
5. ✅ LCD màn hình hiển thị mode, node ID, lỗi
6. ✅ Flash lưu lịch sử lỗi, thống kê
7. ✅ Support cảm biến loại cơ & thông minh
8. ✅ Mã hóa UART bằng AES-128 (tuỳ chọn)

### Dài Hạn
9. ✅ Scale-up lên 4-8 node với CAN/RS485
10. ✅ Machine Learning để dự đoán lưu lượng
11. ✅ Tích hợp GPS/GNSS đồng bộ thời gian
12. ✅ Cloud sync với hệ thống quốc gia

---

## 7. KẾT LUẬN

**Hệ thống điều khiển đèn giao thông này:**

- ✅ **Tốt:** Kiến trúc multi-task rõ ràng, xử lý xả kẹt thông minh, dễ tích hợp Pi
- ❌ **Yếu:** Phụ thuộc Pi quá, giao tiếp không đáng tin, thiếu config linh hoạt, bảo mật thấp
- 🎯 **Phù hợp:** Dự án thử nghiệm, phạm vi nhỏ (2-4 giao lộ), có Pi giám sát
- ⚠️ **Không phù hợp:** Triển khai sản xuất, giao thông cao, yêu cầu độ tin cậy cao

**Đánh giá tổng thể:** 7/10 - Hệ thống tốt cho mục đích học tập/nghiên cứu, cần cải thiện nhiều điểm cho production.

---

**Tài liệu lập bởi:** System Analysis Team  
**Thời gian phân tích:** 23/04/2026  
**Mã dự án:** Traffic Light Control v1.0
