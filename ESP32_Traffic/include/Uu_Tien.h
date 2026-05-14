#pragma once
#include "Thong_tin_he_thong.h"
#include "ChuyenTrangThai.h"

// ============================================================
// Uu_Tien.h — Xử lý pha XẢ KẸT (đèn xanh full, không đếm ngược)
//
//  Vào pha này khi Pi gửi 'A' (Node A) hoặc 'B' (Node B).
//  Đèn xanh bật liên tục, màn hình tắt.
//
//  Thoát khỏi pha (2 trường hợp):
//   1. Nhận lệnh 'a'/'b'  (XuLyLenh đã lọc đúng node, gọi sang_vang_dem)
//      → Đã được XuLyLenh xử lý trực tiếp trước khi cap_nhat() chạy.
//   2. Timeout > 150 giây → tự động thoát (xử lý tại đây)
//
//  Sau cả 2 trường hợp: VANG_DEM 5s → gửi "run" → CHO_MODE_MOI
// ============================================================
class Uu_Tien {
public:
    // Gọi mỗi 10ms khi trangThai == XA_KET
    void cap_nhat(uint32_t thoiGianTroi, ThongTinHeThong& tt) {
        // --- Debug: Log mỗi 5 giây ---
        if (thoiGianTroi % 5000 == 0) {
            Serial.printf("[UU_TIEN] [%lu ms] Dang XA_KET | Con: %lu giay (max 150s) | Node: %s\n",
                          tt.hien_tai,
                          (ThoiGian::GIOI_HAN_UU_TIEN - thoiGianTroi) / 1000,
                          (tt.nodeId == NodeID::NODE_A ? "A" : "B"));
        }
        
        // --- Timeout: quá 150 giây không có lệnh dừng → tự thoát ---
        if (thoiGianTroi >= ThoiGian::GIOI_HAN_UU_TIEN) 
        {
            Serial.printf("[UU_TIEN_TIMEOUT] [%lu ms] Timeout 150s -> Sang VANG_DEM\n", tt.hien_tai);
            tt.daGuiRun = false;
            ChuyenTrangThai::sang_vang_dem(tt);    
        }
    }
};