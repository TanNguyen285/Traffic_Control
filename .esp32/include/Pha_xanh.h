#pragma once
#include "Thong_tin_he_thong.h"
#include "ChuyenTrangThai.h"

// ============================================================
// PhaXanh.h — Xử lý pha đèn XANH
//
//  Handshake (chỉ Node A):
//    Khi còn đúng 2 giây → gửi "run" về Pi 1 lần duy nhất.
//    Pi dùng tín hiệu này để chuẩn bị đồng bộ Node B.
// ============================================================
class PhaXanh {
public:
    // Gọi mỗi 10ms khi trangThai == XANH
    void cap_nhat(uint32_t thoiGianTroi, ThongTinHeThong& tt) 
    {   
         uint32_t   Time_ConLai = 0;
         if (tt.tong_tg_xanh > thoiGianTroi) {
            Time_ConLai = tt.tong_tg_xanh - thoiGianTroi;
        }
       
        // Cập nhật màn hình đếm ngược
        tt.man->hien_thi_so(ChuyenTrangThai::sang_giay(Time_ConLai));

        // --- Debug: Log countdown mỗi giây ---
        if (thoiGianTroi % 1000 == 0) {
            Serial.printf("[XANH] [%lu ms] Con lai: %u giay | Node: %s | Mode: m%u\n",
                          tt.hien_tai, 
                          ChuyenTrangThai::sang_giay(Time_ConLai),
                          (tt.nodeId == NodeID::NODE_A ? "A" : "B"),
                          tt.che_do_hien_tai);
        }

        // --- Handshake: Node A gửi "run" khi xanh còn 2 giây ---
        if (!tt.daGuiRun && Time_ConLai <= ThoiGian::GUI_RUN_NODE_A) 
        {
            tt.uart->gui_ve_pi("run");
            tt.daGuiRun = true;
            Serial.printf("[SEND] [%lu ms] Gui 'run' ve Pi | Node A con %u giay\n", 
                          tt.hien_tai, ChuyenTrangThai::sang_giay(Time_ConLai));
        }

        // --- Kết thúc pha XANH → chuyển sang VÀNG ---
        if (thoiGianTroi >= tt.tong_tg_xanh) {
            tt.daGuiRun = false;
            ChuyenTrangThai::sang_vang(tt);
        }
    }
};