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
        if (tt.co_lenh_moi) {
        tt.tong_tg_xanh    = ThoiGian::TG_XANH[tt.che_do_moi];
        tt.che_do_hien_tai = tt.che_do_moi;
        tt.co_lenh_moi     = false;
        }
        tt.tg_xanh_chot = tt.tong_tg_xanh;
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
        if (tt.co_lenh_moi) {
        tt.tong_tg_xanh    = ThoiGian::TG_XANH[tt.che_do_moi];
        tt.che_do_hien_tai = tt.che_do_moi;
        tt.co_lenh_moi     = false;
        }
        tt.tg_do_chot = tt.tong_tg_xanh + ThoiGian::TG_VANG;
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

        inline void sang_do_dem(ThongTinHeThong& tt) {
        tt.trangThai      = TrangThai::DO_DEM;
        tt.thoiDiemBatDau = tt.hien_tai;
        Serial.printf("[STATE] [%lu ms] DO DEM - Sau XA KET | Thoi gian: 5 giay | Doi Pi gui mode moi\n", tt.hien_tai);
        tt.co_lenh_moi    = false;   
        tt.daGuiRun       = false;
        tt.den->bat_do();
        tt.man->hien_thi_so((uint8_t)(ThoiGian::DO_DEM_HET_UU_TIEN / 1000));
    }

    inline void kich_hoat_uu_tien(ThongTinHeThong& tt) {
    tt.co_lenh_uu_tien = false;
    bool laCuaMinh = (tt.nodeId == NodeID::NODE_A && tt.lenh_uu_tien == 0) ||
                     (tt.nodeId == NodeID::NODE_B && tt.lenh_uu_tien == 1);
    if (laCuaMinh) {
        Serial.printf("[UU_TIEN] [%lu ms] Kich hoat XA_KET\n", tt.hien_tai);
        sang_xa_ket(tt);
    } else {
        Serial.printf("[UU_TIEN] [%lu ms] Kich hoat EP_DO\n", tt.hien_tai);
        sang_ep_do(tt);
    }
}
        
inline void bat_dau_chu_ky(ThongTinHeThong& tt) {
    // 1. Chạy pha dựa trên biến trạng thái hiện tại
    if (tt.luotTiepTheo_LaXanh) {
        sang_xanh(tt);
        // Sau khi kích hoạt Xanh, chuẩn bị cho lượt tới là Đỏ
        tt.luotTiepTheo_LaXanh = false; 
    } else {
        sang_do(tt);
        // Sau khi kích hoạt Đỏ, chuẩn bị cho lượt tới là Xanh
        tt.luotTiepTheo_LaXanh = true;
    }
    
    Serial.printf("[SWITCH] Node %c chuyen pha. Luot toi se la: %s\n", 
                  (tt.nodeId == NodeID::NODE_A ? 'A' : 'B'),
                  (tt.luotTiepTheo_LaXanh ? "XANH" : "DO"));
}


    inline void sang_cho_mode_moi(ThongTinHeThong& tt) {
    // Kiểm tra buffer TRƯỚC — nếu đã có mode thì chạy luôn
    if (tt.co_lenh_moi) {
        tt.che_do_hien_tai = tt.che_do_moi;
        tt.tong_tg_xanh    = ThoiGian::TG_XANH[tt.che_do_moi];
        tt.co_lenh_moi     = false;
        tt.daGuiRun = false;
        Serial.printf("[MODE_APPLY] [%lu ms] Co mode m%u san sang -> Chay luon\n",
                      tt.hien_tai, tt.che_do_hien_tai);
        bat_dau_chu_ky(tt);
        return;  // ← quan trọng, không xuống dưới
    }

    // Không có mode → mới chờ
    Serial.printf("[STATE] [%lu ms] CHO_MODE_MOI - Cho Pi phan hoi\n", tt.hien_tai);
    tt.trangThai      = TrangThai::CHO_MODE_MOI;
    tt.thoiDiemBatDau = tt.hien_tai;
    tt.den->tat_tat_ca();
    tt.man->xoa();
}

    // Node A → XANH trước; Node B → ĐỎ trước (đối nghịch ngã tư)

} 