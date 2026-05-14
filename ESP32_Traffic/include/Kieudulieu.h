#pragma once
#include <stdint.h>

// Trạng thái hoạt động của hệ thống
enum class TrangThai : uint8_t {
    CHO_KHOI_DONG = 0,  // Chờ nhấn nút để bắt đầu
    GREEN,               // Đang bật đèn xanh, đếm ngược
    YELLOW,               // Đang bật đèn vàng, đếm ngược
    RED,                 // Đang bật đèn đỏ, đếm ngược
    UU_TIEN,             // Xả kẹt: xanh liên tục (tối đa 150s)
    VANG_DEM,           // Đèn vàng đệm 5s sau khi thoát xả kẹt
    DO_DEM,
    EP_DO,              // Bị ép đỏ vì node kia đang xả kẹt — chờ lệnh dừng
    CHO_MODE_MOI        // Đã gửi "run", chờ Pi gửi mode mới
};

// Định danh Node — đọc từ GPIO lúc boot
enum class NodeID : uint8_t {
    NODE_A = 0,         // GPIO4 = LOW  → Node A (bắt đầu bằng đèn XANH)
    NODE_B = 1          // GPIO4 = HIGH → Node B (bắt đầu bằng đèn ĐỎ)
};

// Loại lệnh nhận từ Raspberry Pi qua UART
enum class LoaiLenh : uint8_t {
    MODE,               // "m0" .. "m4"  — cập nhật chu kỳ
    BAT_UU_TIEN,         // 'A' (Node A) / 'B' (Node B) — bắt đầu xả kẹt
    TAT_UU_TIEN,          // 'a' (Node A) / 'b' (Node B) — dừng xả kẹt
    BAT_DAU      
};

// Cấu trúc lệnh được đẩy vào FreeRTOS Queue
struct LenhNhan {
    LoaiLenh loai;
    uint8_t  giaTri;    // MODE: 0-4 | XA_KET_BAT/TAT: 0='A/a', 1='B/b'
};

// Cấu trúc thời gian 1 chu kỳ đèn (ms)
struct ChuKy {
    uint32_t time_g;
  //uint32_t time_y;
  //uint32_t time_r;
};