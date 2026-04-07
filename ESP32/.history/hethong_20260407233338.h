#pragma once
#include <Arduino.h>

class dieu_khien_pin {
public:
    dieu_khien_pin(uint8_t px, uint8_t pd, uint8_t pv) : _px(px), _pd(pd), _pv(pv) {}
    
    void bat_dau() {
        pinMode(_px, OUTPUT); pinMode(_pd, OUTPUT); pinMode(_pv, OUTPUT);
        tat_het();
    }
    void den_xanh(bool bat) { digitalWrite(_px, bat ? HIGH : LOW); }
    void den_do(bool bat)   { digitalWrite(_pd, bat ? HIGH : LOW); }
    void den_vang(bool bat) { digitalWrite(_pv, bat ? HIGH : LOW); }
    void tat_het() { den_xanh(0); den_do(0); den_vang(0); }

private:
    uint8_t _px, _pd, _pv;
};

class bo_dem_gio {
public:
    explicit bo_dem_gio(dieu_khien_pin& p) : _p(p) {}

    uint32_t thoi_gian_mode(uint8_t m) {
        const uint32_t bang_giay[] = {10, 15, 20, 25, 30}; 
        return (m >= 1 && m <= 4) ? bang_giay[m-1] : bang_giay[0];
    }

    void chay_tu_dong(uint8_t m) {
        if (!_dang_chay) return;
        uint32_t bay_gio = millis();
        uint32_t gioi_han = thoi_gian_mode(m) * 1000;
        uint32_t da_troi_qua = bay_gio - _luc_bat_dau;

        // Con 5 giay cuoi thi hien bang LCD (den vang)
        if (da_troi_qua >= (gioi_han - 5000)) _p.den_vang(1);
        else _p.den_vang(1) == 0; // Tat khi chua den luc

        if (da_troi_qua >= gioi_han) {
            _la_den_xanh = !_la_den_xanh;
            _luc_bat_dau = bay_gio;
            _cap_nhat();
        }
    }

    void bat() { _dang_chay = true; _luc_bat_dau = millis(); _la_den_xanh = true; _cap_nhat(); }
    void tat() { _dang_chay = false; _p.tat_het(); }
    bool co_dang_chay_khong() { return _dang_chay; }

private:
    dieu_khien_pin& _p; uint32_t _luc_bat_dau; bool _dang_chay = false; bool _la_den_xanh = true;
    void _cap_nhat() { _p.den_xanh(_la_den_xanh); _p.den_do(!_la_den_xanh); }
};

class tram_bi_ket {
public:
    tram_bi_ket(dieu_khien_pin& p, bool xanh) : _p(p), _mau_xanh(xanh) {}
    void ep_dung_yen(bool bat) {
        _dang_bi_ket = bat;
        if (_dang_bi_ket) { _p.den_xanh(_mau_xanh); _p.den_do(!_mau_xanh); _p.den_vang(0); }
    }
    bool co_dang_bi_ket_khong() { return _dang_bi_ket; }
    void xa_ket() { _dang_bi_ket = false; }
private:
    dieu_khien_pin& _p; bool _mau_xanh; bool _dang_bi_ket = false;
};

class tram_thong_thoang {
public:
    void co_tin_hieu() { _thong = true; }
    bool check_xem_thong_chua() { return _thong; }
    void xong_roi() { _thong = false; }
private:
    bool _thong = false;
};

struct tin_nhan { char chu_cai = ' '; uint8_t con_so = 0; };
class nhan_lenh_uart {
public:
    tin_nhan doc_tin_nhan() {
        tin_nhan t;
        if (Serial.available()) {
            String s = Serial.readStringUntil('\n');
            s.trim();
            if (s.length() == 0) return t;

            if (s[0] == 'm') { t.chu_cai = 'm'; t.con_so = s.substring(1).toInt(); }
            else if (s == "A") t.chu_cai = 'A';
            else if (s == "B") t.chu_cai = 'B';
            else if (s == "a") t.chu_cai = 'a';
            else if (s == "b") t.chu_cai = 'b';
        }
        return t;
    }
};