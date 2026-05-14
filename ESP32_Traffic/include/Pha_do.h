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
    void cap_nhat(uint32_t thoiGianTroi, ThongTinHeThong& tt)
    {
        // Dùng tg_do_chot đã chốt lúc vào pha — không tính lại
        uint32_t Time_ConLai = ChuyenTrangThai::time_ConLai(
                                   thoiGianTroi, tt.tg_do_chot);

        // Cập nhật màn hình đếm ngược
        tt.man->hien_thi_so(ChuyenTrangThai::sang_giay(Time_ConLai));

        // Debug log mỗi giây
        if (thoiGianTroi % 1000 == 0) {
            Serial.printf("[DO] [%lu ms] Con lai: %u giay | Node: %s | Mode: m%u\n",
                          tt.hien_tai,
                          ChuyenTrangThai::sang_giay(Time_ConLai),
                          (tt.nodeId == NodeID::NODE_A ? "A" : "B"),
                          tt.che_do_hien_tai);
        }

        // Handshake: gửi "run" khi còn 5s
        if (!tt.daGuiRun && Time_ConLai <= ThoiGian::GUI_RUN_NODE_B)
        {
            tt.uart->gui_ve_pi("run");
            tt.daGuiRun = true;
            Serial.printf("[SEND] [%lu ms] Gui 'run' ve Pi | con %u giay\n",
                          tt.hien_tai, ChuyenTrangThai::sang_giay(Time_ConLai));
        }

        // Kết thúc pha ĐỎ
        if (thoiGianTroi >= tt.tg_do_chot)
        {
            if (tt.co_lenh_uu_tien) {
                // Có lệnh xả kẹt đang chờ → kích hoạt
                ChuyenTrangThai::kich_hoat_uu_tien(tt);
            } else {
                // Bình thường → sang xanh
                // (sang_xanh sẽ tự áp co_lenh_moi nếu có)
                ChuyenTrangThai::sang_xanh(tt);
            }
        }
    }
};