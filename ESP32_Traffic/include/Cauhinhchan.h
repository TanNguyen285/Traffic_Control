#pragma once
#include "Kieudulieu.h"
 
// ------------------------------------------------------------
// Chân GPIO
// ------------------------------------------------------------
namespace Pin {
    // Đèn LED giao thông 
    constexpr uint8_t DEN_XANH          = 16;
    constexpr uint8_t DEN_VANG          = 4;
    constexpr uint8_t DEN_DO            = 17;
 
    constexpr uint8_t MAX7219_DIN       = 5;
    constexpr uint8_t MAX7219_CLK       = 18;
    constexpr uint8_t MAX7219_CS        = 19;
 
    // Nút khởi động: nhấn-thả → bắt đầu chu kỳ (active LOW, pull-up nội)
    constexpr uint8_t BUTTON_START     = 13;   // GPIO13 / BOOT button
 
    // Chọn Node ID: LOW = Node A, HIGH = Node B (dùng pull-up nội)
    constexpr uint8_t NODE_ID      = 25;
 
    // UART2 giao tiếp với Raspberry Pi
    constexpr uint8_t UART_RX           = 27;
    constexpr uint8_t UART_TX           = 26;
}
 
// ------------------------------------------------------------
// Bảng thời gian chu kỳ theo Mode (ms)
//   Quy tắc: "hết đèn đỏ" mới áp dụng mode mới nếu đang chạy
// ------------------------------------------------------------
namespace ThoiGian {
    constexpr uint32_t TG_XANH[5] = { 27000, 17000, 42000, 57000, 87000 }; // m0 -> m4

    constexpr uint32_t TG_VANG  = 3000;

    // Timeout CHO_MODE_MOI: nếu Pi không gửi mode sau Xs → tự chạy m0
    constexpr uint32_t CHO_MODE_MOI_TIMEOUT_MS = 5000;  // 5 giây
 
    // Đèn vàng đệm sau khi kết thúc xả kẹt (5 giây)
    constexpr uint32_t VANG_DEM_HET_UU_TIEN   = 5000;
    constexpr uint32_t DO_DEM_HET_UU_TIEN   = 5000;
 
    // Timeout tự động thoát xả kẹt nếu không nhận lệnh dừng (150 giây)
    constexpr uint32_t GIOI_HAN_UU_TIEN     = 150000;
 
    // Handshake: Node A gửi "run" khi đèn xanh còn 2 giây
    constexpr uint32_t GUI_RUN_NODE_A  = 2000;
 
    // Handshake: Node B gửi "run" khi đèn đỏ còn 5 giây
    constexpr uint32_t GUI_RUN_NODE_B    = 5000;
 
    // Chống rung nút nhấn (ms)
    constexpr uint32_t CHONG_NHIEU  = 50;
}
 
// ------------------------------------------------------------
// Cấu hình UART
// ------------------------------------------------------------
namespace CauHinhUART {
    constexpr uint32_t BAUD_RATE     = 115200;
}