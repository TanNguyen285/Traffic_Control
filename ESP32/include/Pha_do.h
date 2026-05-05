#pragma once
#include "Thong_tin_he_thong.h"
#include "ChuyenTrangThai.h"

// ============================================================
// PhaDo.h — Xử lý pha đèn ĐỎ
//
//  Handshake (chỉ Node B):
//    Khi còn đúng 5 giây → gửi "run" về Pi 1 lần duy nhất.
//    Pi dùng tín hiệu này để chuẩn bị gửi mode cho chu kỳ mới.
//
//  Kết thúc pha ĐỎ:
//    1. Áp dụng mode đệm (nếu có) nhận được trong chu kỳ vừa rồi
//    3. Chuyển sang XANH
// ============================================================
class PhaDo {
public:
    // Gọi mỗi 10ms khi trangThai == DO
    void cap_nhat(uint32_t thoiGianTroi, ThongTinHeThong& tt) // tt -> thong tin
    {
        
        // 1. TÍNH TOÁN: Tổng thời gian Đỏ = Xanh hiện tại + Vàng (3s)
        uint32_t TongGiayDo = tt.tong_tg_xanh + ThoiGian::TG_VANG;

    // 2. TÍNH THỜI GIAN CÒN LẠI    
        uint32_t Time_ConLai = ChuyenTrangThai::time_ConLai(thoiGianTroi, TongGiayDo);

        // Cập nhật màn hình đếm ngược
        tt.man->hien_thi_so(ChuyenTrangThai::sang_giay(Time_ConLai));

        // --- Debug: Log countdown mỗi giây ---
        if (thoiGianTroi % 1000 == 0) {
            Serial.printf("[DO] [%lu ms] Con lai: %u giay | Node: %s | Mode: m%u\n",
                          tt.hien_tai,
                          ChuyenTrangThai::sang_giay(Time_ConLai),
                          (tt.nodeId == NodeID::NODE_A ? "A" : "B"),
                          tt.che_do_hien_tai);
        }

        if (!tt.daGuiRun && Time_ConLai <= ThoiGian::GUI_RUN_NODE_B) 
        {
            tt.uart->gui_ve_pi("run");
            tt.daGuiRun = true;
            Serial.printf("[SEND] [%lu ms] Gui 'run' ve Pi | Node B con %u giay\n",
                          tt.hien_tai, ChuyenTrangThai::sang_giay(Time_ConLai));
        }

        // --- Kết thúc pha ĐỎ ---
        if (thoiGianTroi >= TongGiayDo) 
        {
            // Áp dụng mode đã đệm (nếu có), bỏ qua nếu không có
            if (tt.co_lenh_moi) 
            {
                Serial.printf("[MODE_APPLY] [%lu ms] Ap dung mode m%u (chu ky tiep theo)\n",
                              tt.hien_tai, tt.che_do_moi);
                tt.tong_tg_xanh = ThoiGian::TG_XANH[tt.che_do_moi];
                tt.che_do_hien_tai = tt.che_do_moi;  // Update chế độ hiện tại
                tt.co_lenh_moi  = false;
            }
            ChuyenTrangThai::sang_xanh(tt);  // Bắt đầu chu kỳ mới
        }
    }
};