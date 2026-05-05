#pragma once
#include "Thong_tin_he_thong.h"
#include "DenGiaoThong.h"
#include "Led7Doan.h"
#include "BoXuLyUART.h"

// ============================================================
// ChuyenTrangThai.h — Hàm chuyển pha, dùng chung cho mọi module
//   Tất cả inline để không sinh symbol trùng khi include nhiều nơi.
// ============================================================
namespace ChuyenTrangThai {

    // Tính số giây còn lại (làm tròn lên), tránh hiển thị "0" sớm
    inline uint32_t time_ConLai(uint32_t da_troi, uint32_t tong) {
        return (da_troi < tong) ? (tong - da_troi) : 0;
    }

    inline uint8_t sang_giay(uint32_t conLai_ms) {
        return (uint8_t)((conLai_ms + 999) / 1000);
    }

    // ----------------------------------------------------------
    inline void sang_xanh(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::GREEN;
        tt.thoiDiemBatDau = tt.hien_tai;
        tt.daGuiRun       = false;
        tt.den->bat_xanh();
        tt.man->hien_thi_so((uint8_t)(tt.tong_tg_xanh/ 1000));
        Serial.printf("[COLOR] ✓ BAT DEN XANH [%lu ms] | Node: %s | Thoi gian: %lu giay\n", 
                      tt.hien_tai, (tt.nodeId == NodeID::NODE_A ? "A" : "B"), tt.tong_tg_xanh/1000);
    }

    inline void sang_vang(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::YELLOW;
        tt.thoiDiemBatDau = tt.hien_tai;
        tt.den->bat_vang();
        tt.man->hien_thi_so((uint8_t)(ThoiGian::TG_VANG / 1000));
        Serial.printf("[COLOR] ★ BAT DEN VANG [%lu ms] | Thoi gian: %u giay\n", 
                      tt.hien_tai, (uint8_t)(ThoiGian::TG_VANG / 1000));
    }

    inline void sang_do(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::RED;
        tt.thoiDiemBatDau = tt.hien_tai;
        tt.daGuiRun       = false;
        tt.den->bat_do();
        uint32_t tg_do = tt.tong_tg_xanh + ThoiGian::TG_VANG;
        Serial.printf("[COLOR] ⊗ BAT DEN DO [%lu ms] | Thoi gian: %u giay\n", 
                      tt.hien_tai, (uint8_t)(tg_do / 1000));
        tt.man->hien_thi_so((uint8_t)(tg_do / 1000));
    }

    inline void sang_xa_ket(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::UU_TIEN;
        tt.thoiDiemBatDau = tt.hien_tai;
        Serial.printf("[STATE] [%lu ms] CHU KY UU TIEN (XA KET) - Node: %s | Dung toi da 150s\n", 
                      tt.hien_tai, (tt.nodeId == NodeID::NODE_A ? "A" : "B"));
        tt.den->bat_xanh();
        tt.man->xoa();
    }

    // Node kia bật xả kẹt → ép đỏ ngay lập tức, không đếm ngược
    // Thoát khi nhận lệnh dừng ('a'/'b') rồi sang XANH_CUOI
    inline void sang_ep_do(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::EP_DO;
        tt.thoiDiemBatDau = tt.hien_tai;
        Serial.printf("[STATE] [%lu ms] EP DO (Node %s khac dang XA KET)\n", 
                      tt.hien_tai, (tt.nodeId == NodeID::NODE_A ? "B" : "A"));
        tt.den->bat_do();
        tt.man->xoa();
    }

    inline void sang_vang_dem(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::VANG_DEM;
        tt.thoiDiemBatDau = tt.hien_tai;
        Serial.printf("[STATE] [%lu ms] VANG DEM - Sau XA KET | Thoi gian: 5 giay | Doi Pi gui mode moi\n", tt.hien_tai);
        tt.co_lenh_moi    = false;   
        tt.daGuiRun       = false;
        tt.den->bat_vang();
        tt.man->hien_thi_so((uint8_t)(ThoiGian::VANG_DEM_HET_UU_TIEN / 1000));
    }

    inline void sang_cho_mode_moi(ThongTinHeThong& tt) {
        Serial.printf("[STATE] [%lu ms] CHO_MODE_MOI - Tat tat ca den, cho Pi phan hoi (timeout 10s)\n", tt.hien_tai);
        tt.trangThai = TrangThai::CHO_MODE_MOI;
        tt.den->tat_tat_ca();
        tt.man->xoa();
    }

    // Node A → XANH trước; Node B → ĐỎ trước (đối nghịch ngã tư)
    inline void bat_dau_chu_ky(ThongTinHeThong& tt) {
        (tt.nodeId == NodeID::NODE_A) ? sang_xanh(tt) : sang_do(tt);
    }

} // namespace ChuyenTrangThai