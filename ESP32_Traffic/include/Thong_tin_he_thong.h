#pragma once
#include "Kieudulieu.h"
#include "Cauhinhchan.h"

// Forward declarations — tránh circular include
class DenGiaoThong;
class Led7Doan;
class BoXuLyUART;

// ============================================================
//   Trạng thái dùng chung cho tất cả module
// ============================================================
struct ThongTinHeThong {
    // --- Logic ---
    TrangThai   trangThai      = TrangThai::CHO_KHOI_DONG;
    uint32_t    tong_tg_xanh   = ThoiGian::TG_XANH[0];
    uint32_t tg_xanh_chot = 0;   // Chốt khi vào pha XANH
    uint32_t tg_do_chot   = 0;   // Chốt khi vào pha ĐỎ
    // --- lenh nhan tu Pi ---
    bool        co_lenh_moi    = false; // Có lệnh mới đang chờ áp dụng không?
    uint8_t     che_do_moi      = 0;    // Chế độ (0-4) Pi vừa gửi xuống
    uint8_t     che_do_hien_tai = 0;    // Chế độ (0-4) đang chạy hiện tại
    // --- Buffer Uu Tien ---
    bool    co_lenh_uu_tien    = false;
    uint8_t lenh_uu_tien       = 0;
    bool    luotTiepTheo_LaXanh = true;  // Node A=true, Node B=false
    // --- Quan ly real-time ---
    uint32_t    hien_tai            = 0;    // millis() hiện tại (cập nhật mỗi tick)
    uint32_t    thoiDiemBatDau = 0;   // millis() lúc bắt đầu pha hiện tại
    // --- Cờ và Định danh ---
    bool        daGuiRun       = false;
    NodeID      nodeId         = NodeID::NODE_A;

    // --- Hardware (con trỏ, khởi tạo trong MayTrangThai::khoi_dong) ---
    DenGiaoThong*    den  = nullptr;
    Led7Doan*   man  = nullptr;
    BoXuLyUART* uart = nullptr;
};