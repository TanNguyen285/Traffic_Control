#pragma once
#include <Arduino.h>
#include "Thong_tin_he_thong.h"
#include "ChuyenTrangThai.h"
#include "XuLyLenh.h"
#include "Pha_xanh.h"
#include "Pha_do.h"
#include "Uu_Tien.h"
#include "DenGiaoThong.h"
#include "Led7Doan.h"
#include "BoXuLyUART.h"

// ============================================================
// MayTrangThai.h — Coordinator mỏng
//   Kết nối phần cứng với các module xử lý pha.
//   Tự quản lý: nút khởi động (debounce), VANG, VANG_DEM,
//   CHO_MODE_MOI — những pha không có logic phức tạp.
// ============================================================
class BoDieuKhienNgaTu {
public:
    BoDieuKhienNgaTu(NodeID nodeId, DenGiaoThong& den, Led7Doan& man, BoXuLyUART& uart) {
        _ctx.nodeId = nodeId;
        _ctx.den    = &den;
        _ctx.man    = &man;
        _ctx.uart   = &uart;
    }

    void khoi_dong() {
        pinMode(Pin::BUTTON_START, INPUT_PULLUP);
        _nutTrangThaiCu      = digitalRead(Pin::BUTTON_START);
        _nutThoiGianDebounce = 0;
        _nutDangNhan         = false;
        _ctx.trangThai = TrangThai::CHO_KHOI_DONG;

        // ← THÊM: set đúng giá trị mặc định theo nodeId
        _ctx.luotTiepTheo_LaXanh = (_ctx.nodeId == NodeID::NODE_A) ? true : false;

        _ctx.den->tat_tat_ca();
        _ctx.man->xoa();
}

    // Gọi trước cap_nhat() — drain queue trước khi update state
    void nhan_lenh(const LenhNhan& lenh) {
        _xuLyLenh.nhan_lenh(lenh, _ctx);
    }

    // Gọi mỗi ~10ms với millis() hiện tại
   void cap_nhat(uint32_t hien_tai) 
{
    _ctx.hien_tai = hien_tai;

    if (_ctx.trangThai == TrangThai::CHO_KHOI_DONG) {
        _xu_ly_nut_nhan();
        return;
    }

    // Log định kỳ khi đang chạy để biết máy không treo
    if (hien_tai % 1000 == 0) { 
        const char* ten_trang_thai[] = {
            "CHO_KHOI_DONG", "GREEN", "YELLOW", "RED", 
            "UU_TIEN", "VANG_DEM", "EP_DO", "CHO_MODE_MOI"
        };
        Serial.printf("[LOOP] [%lu ms] Trang thai: %s | Node: %s | Che_do: m%u\n", 
                      hien_tai,
                      ten_trang_thai[(int)_ctx.trangThai],
                      _ctx.nodeId == NodeID::NODE_A ? "A" : "B",
                      _ctx.che_do_hien_tai);
    }
    

        uint32_t dt = hien_tai - _ctx.thoiDiemBatDau;

        switch (_ctx.trangThai) {
            case TrangThai::GREEN:        _phaXanh.cap_nhat(dt, _ctx);  break;
            case TrangThai::YELLOW:        _xu_ly_vang(dt);               break;
            case TrangThai::RED:          _phaDo.cap_nhat(dt, _ctx);     break;
            case TrangThai::UU_TIEN:      _xaKet.cap_nhat(dt, _ctx);    break;
            case TrangThai::EP_DO: 
            // Nếu thời gian ở trạng thái ÉP ĐỎ (dt) >= 150 giây (GIOI_HAN_UU_TIEN)
            if (dt >= ThoiGian::GIOI_HAN_UU_TIEN) {
                Serial.printf("[TIMEOUT] Node kia xa ket qua lau (150s) -> Tu thoat EP_DO\n");
                ChuyenTrangThai::sang_do_dem(_ctx); 
            }
            break;
            case TrangThai::VANG_DEM:    _xu_ly_vang_dem(dt);           break;
            case TrangThai::CHO_MODE_MOI: _xu_ly_cho_mode_moi(dt); break;
            case TrangThai::DO_DEM: _xu_ly_do_dem(dt);              break;
            default: break;
        }
    }

    TrangThai lay_trang_thai() const { return _ctx.trangThai; }
    NodeID    lay_node_id()    const { return _ctx.nodeId; }

private:
    ThongTinHeThong _ctx;
    XuLyLenh        _xuLyLenh;
    PhaXanh         _phaXanh;
    PhaDo           _phaDo;
    Uu_Tien         _xaKet;

    int      _nutTrangThaiCu       = HIGH;
    uint32_t _nutThoiGianDebounce  = 0;
    bool     _nutDangNhan          = false;

    void _xu_ly_vang(uint32_t dt) {
        uint32_t conLai_ms = ChuyenTrangThai::time_ConLai(dt, ThoiGian::TG_VANG);
        _ctx.man->hien_thi_so(ChuyenTrangThai::sang_giay(conLai_ms));
        
        // --- Debug: Log countdown mỗi giây ---
        if (dt % 1000 == 0) {
            Serial.printf("[VANG] [%lu ms] Con lai: %u giay\n",
                          _ctx.hien_tai, ChuyenTrangThai::sang_giay(conLai_ms));
        }
        
        if (dt >= ThoiGian::TG_VANG) {
        if (_ctx.co_lenh_uu_tien) {
            ChuyenTrangThai::kich_hoat_uu_tien(_ctx);
            } else {
            ChuyenTrangThai::sang_do(_ctx);
            }
        }
    }

    void _xu_ly_vang_dem(uint32_t dt) {
        uint32_t conLai_ms = ChuyenTrangThai::time_ConLai(dt, ThoiGian::VANG_DEM_HET_UU_TIEN);
        _ctx.man->hien_thi_so(ChuyenTrangThai::sang_giay(conLai_ms));
        
        // --- Debug: Log countdown ---
        if (dt % 1000 == 0) {
            Serial.printf("[VANG_DEM] [%lu ms] Con lai: %u giay | Doi Pi phan hoi mode moi\n",
                          _ctx.hien_tai, ChuyenTrangThai::sang_giay(conLai_ms));
        }
        
        // --- HANDSHAKE: Gửi "run" về Pi khi sắp hết 5 giây vàng ---
        if (!_ctx.daGuiRun && conLai_ms <= 5000) 
        { 
            _ctx.uart->gui_ve_pi("run");
            _ctx.daGuiRun = true;
            Serial.printf("[SEND] [%lu ms] Gui 'run' ve Pi (VANG_DEM) | Con %u giay\n",
                          _ctx.hien_tai, ChuyenTrangThai::sang_giay(conLai_ms));
        }

        if (dt >= ThoiGian::VANG_DEM_HET_UU_TIEN) {
            ChuyenTrangThai::sang_cho_mode_moi(_ctx); 
        }

}

    void _xu_ly_do_dem(uint32_t dt) {
        uint32_t conLai_ms = ChuyenTrangThai::time_ConLai(dt, ThoiGian::DO_DEM_HET_UU_TIEN);
        _ctx.man->hien_thi_so(ChuyenTrangThai::sang_giay(conLai_ms));
        
        // --- Debug: Log countdown ---
        if (dt % 1000 == 0) {
            Serial.printf("[DO_DEM] [%lu ms] Con lai: %u giay | Doi Pi phan hoi mode moi\n",
                          _ctx.hien_tai, ChuyenTrangThai::sang_giay(conLai_ms));
        }
        
        // --- HANDSHAKE: Gửi "run" về Pi khi sắp hết 5 giây vàng ---
        if (!_ctx.daGuiRun && conLai_ms <= 5000) 
        { 
            _ctx.uart->gui_ve_pi("run");
            _ctx.daGuiRun = true;
            Serial.printf("[SEND] [%lu ms] Gui 'run' ve Pi (DO_DEM) | Con %u giay\n",
                          _ctx.hien_tai, ChuyenTrangThai::sang_giay(conLai_ms));
        }
        if (dt >= ThoiGian::VANG_DEM_HET_UU_TIEN) {
            ChuyenTrangThai::sang_cho_mode_moi(_ctx);
        }

}

    // -----------------------------------------------------------
    // CHO_MODE_MOI: nếu Pi không phản hồi sau 5s → fallback m0
    // -----------------------------------------------------------
    void _xu_ly_cho_mode_moi(uint32_t dt) 
    {
        // --- Debug: Log mỗi 1 giây ---
        if (dt % 1000 == 0) {
            Serial.printf("[CHO_MODE] [%lu ms] Cho Pi phan hoi (timeout sau %lu ms)\n",
                          _ctx.hien_tai, (ThoiGian::CHO_MODE_MOI_TIMEOUT_MS - dt));
        }
        
        if (dt >= ThoiGian::CHO_MODE_MOI_TIMEOUT_MS) {
            _ctx.tong_tg_xanh = ThoiGian::TG_XANH[0];   // Reset về m0
            _ctx.co_lenh_moi  = false;
            Serial.printf("[TIMEOUT] [%lu ms] Pi ko phan hoi -> Fallback m0 (30s)\n", _ctx.hien_tai);
            ChuyenTrangThai::bat_dau_chu_ky(_ctx);
        }
    }

    void _xu_ly_nut_nhan() {
        int docPin = digitalRead(Pin::BUTTON_START);
        
        // Thêm dòng này để thấy nó vẫn đang quét (comment out nếu log quá nhiều)
        if (_ctx.hien_tai % 5000 == 0) { 
            Serial.printf("[IDLE] Dang cho nut bam... (GPIO%d: %s)\n", 
                          Pin::BUTTON_START, docPin == LOW ? "LOW" : "HIGH");
        }

        if (docPin != _nutTrangThaiCu) {
            _nutThoiGianDebounce = _ctx.hien_tai;
            _nutTrangThaiCu = docPin;
        }
        
        if ((_ctx.hien_tai - _nutThoiGianDebounce) < ThoiGian::CHONG_NHIEU) return;
        
        if (docPin == LOW  && !_nutDangNhan) { 
            _nutDangNhan = true; 
            Serial.println("[EVENT] Da nhan nut (GND)!");
        }
        
        if (docPin == HIGH && _nutDangNhan)  {
            _nutDangNhan = false;
            Serial.println("[EVENT] Da buong nut -> BAT DAU CHU KY!");
            ChuyenTrangThai::bat_dau_chu_ky(_ctx);
        }
    }
};