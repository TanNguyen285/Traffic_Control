#pragma once
#include "Thong_Tin_He_Thong.h"
#include "ChuyenTrangThai.h"

// ============================================================
// XuLyLenh.h — Nhận lệnh từ Pi, phân loại và xử lý
//
//  Bảng lệnh (Pi gửi giống nhau cho cả 2 node — mỗi node tự lọc):
//
//  Lệnh    LoaiLenh        giaTri    Node nhận
//  -----   ------------    ------    ---------
//  m0-m4   MODE            0-4       Cả 2
//  'A'     XA_KET_BAT      0         Node A
//  'B'     XA_KET_BAT      1         Node B
//  'a'     XA_KET_TAT      0         Node A
//  'b'     XA_KET_TAT      1         Node B
// ============================================================
class XuLyLenh {
public:
    void nhan_lenh(const LenhNhan& lenh, ThongTinHeThong& tt) {
        switch (lenh.loai) {
            case LoaiLenh::MODE:        _case_mode(lenh.giaTri, tt);       break;
            case LoaiLenh::BAT_UU_TIEN:  _case_uu_tien_bat(lenh.giaTri, tt); break;
            case LoaiLenh::TAT_UU_TIEN:  _case_uu_tien_tat(lenh.giaTri, tt); break;
        }
    }

private:
    // ----------------------------------------------------------
    // case MODE: m0 → m4
    //   • Đang chạy (XANH/VANG/DO) → lưu vào bộ đệm, chờ hết ĐỎ
    //   • Đang dừng (CHO_MOI / CHO_KHOI_DONG) → áp dụng ngay
    // ----------------------------------------------------------
    void _case_mode(uint8_t mode, ThongTinHeThong& tt) {
        if (mode > 4) return;

        bool dangChay = (tt.trangThai == TrangThai::GREEN ||
                         tt.trangThai == TrangThai::YELLOW ||
                         tt.trangThai == TrangThai::RED);
        if (dangChay) {
            tt.co_lenh_moi = true;
            tt.che_do_moi   = mode;
            Serial.printf("[LENH] [%lu ms] Nhan MODE m%u | Dang chay -> Dem vao bo dem\n",
                          tt.hien_tai, mode);
        } else {
            tt.tong_tg_xanh = ThoiGian::TG_XANH[mode];
            tt.che_do_hien_tai = mode;  // Update chế độ hiện tại
            tt.co_lenh_moi  = false;
            Serial.printf("[LENH] [%lu ms] Nhan MODE m%u | Dung -> Ap dung ngay\n",
                          tt.hien_tai, mode);
            ChuyenTrangThai::bat_dau_chu_ky(tt);
        }
    }

    // ----------------------------------------------------------
    // case 'A' → bật xả kẹt Node A (giaTri == 0)
    // case 'B' → bật xả kẹt Node B (giaTri == 1)
    //   Chỉ kích hoạt khi đang trong chu kỳ bình thường.
    // ----------------------------------------------------------
void _case_uu_tien_bat(uint8_t nodeNhanLenh, ThongTinHeThong& tt) {
        bool dangChay = (tt.trangThai == TrangThai::GREEN ||
                         tt.trangThai == TrangThai::YELLOW ||
                         tt.trangThai == TrangThai::RED);
        
        // --- ĐOẠN NÀY ĐÃ FIX LỖI CÚ PHÁP CỦA HUYNH ---
        if (_la_lenh_cua_minh(nodeNhanLenh, tt.nodeId)) {
            // Nếu đúng Node mình thì mới bật Xanh full
            if (dangChay) {
                Serial.printf("[LENH] [%lu ms] Nhan BAT_UU_TIEN -> Node %s BAT XA_KET\n",
                              tt.hien_tai, (tt.nodeId == NodeID::NODE_A ? "A" : "B"));
                ChuyenTrangThai::sang_xa_ket(tt);
            }
        } else {
            // Nếu lệnh dành cho Node kia thì mình phải Ép Đỏ
            if (dangChay) {
                Serial.printf("[LENH] [%lu ms] Nhan BAT_UU_TIEN -> Node %s bi EP_DO\n",
                              tt.hien_tai, (tt.nodeId == NodeID::NODE_A ? "A" : "B"));
                ChuyenTrangThai::sang_ep_do(tt);
            }
        }
    }

    // ----------------------------------------------------------
    // case 'a' → dừng xả kẹt Node A (giaTri == 0)
    // case 'b' → dừng xả kẹt Node B (giaTri == 1)
    //   Chuyển sang VANG_DEM 5s → gửi "run" → chờ mode mới.
    // ----------------------------------------------------------
    void _case_uu_tien_tat(uint8_t nodeNhanLenh, ThongTinHeThong& tt) {
        bool laNodeChinh = _la_lenh_cua_minh(nodeNhanLenh, tt.nodeId);
        bool laNodeDoiDien  = !laNodeChinh;
        
        // Kiểm tra đúng Node chính và đang ở trạng thái ưu tiên 
        if (laNodeChinh && tt.trangThai == TrangThai::UU_TIEN) {
            Serial.printf("[LENH] [%lu ms] Nhan TAT_UU_TIEN -> Node %s TAT XA_KET, sang VANG_DEM\n",
                          tt.hien_tai, (tt.nodeId == NodeID::NODE_A ? "A" : "B"));
            tt.daGuiRun = false; 
            ChuyenTrangThai::sang_vang_dem(tt);
        } 
        else if (laNodeDoiDien && tt.trangThai == TrangThai::EP_DO) {
            // Node đối diện đang bị ép đỏ -> Tiếp tục giữ Đỏ cho đến khi Pi gửi Mode mới
            Serial.printf("[LENH] [%lu ms] Nhan TAT_UU_TIEN (node kia) -> Sang CHO_MODE_MOI\n",
                          tt.hien_tai);
            ChuyenTrangThai::sang_cho_mode_moi(tt);
        }
    }

    // Lệnh 'A'/'a' (giaTri=0) thuộc Node A; 'B'/'b' (giaTri=1) thuộc Node B
    bool _la_lenh_cua_minh(uint8_t nodeNhanLenh, NodeID nodeId) {
        return (nodeId == NodeID::NODE_A && nodeNhanLenh == 0) ||
               (nodeId == NodeID::NODE_B && nodeNhanLenh == 1);
    }
};