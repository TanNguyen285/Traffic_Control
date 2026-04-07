#pragma once
#include <Arduino.h>

// 1. dieu_khien_pin: quan ly cac chan den
class dieu_khien_pin {
public:
    dieu_khien_pin(uint8_t px, uint8_t pd, uint8_t pv) : _px(px), _pd(pd), _pv(pv) {}
    
    void batdau() {
        pinMode(_px, OUTPUT); pinMode(_pd, OUTPUT); pinMode(_pv, OUTPUT);
        tathet();
    }
    void xanh(bool on) { digitalWrite(_px, on ? HIGH : LOW); }
    void do_(bool on)  { digitalWrite(_pd, on ? HIGH : LOW); }
    void vang(bool on) { digitalWrite(_pv, on ? HIGH : LOW); }
    void tathet() { xanh(0); do_(0); vang(0); }

private:
    uint8_t _px, _pd, _pv;
};

// 2. model_timer: quan ly thoi gian tu dong
class model_timer {
public:
    explicit model_timer(dieu_khien_pin& p) : _p(p) {}

    uint32_t bangtimer(uint8_t m) {
        const uint32_t t[] = {10, 15, 20, 25, 30}; 
        return (m >= 1 && m <= 4) ? t[m-1] : t[0];
    }

    void chay_auto(uint8_t m) {
        if (!_kichhoat) return;
        uint32_t baygio = millis();
        uint32_t gioihan = bangtimer(m) * 1000;
        uint32_t troiqua = baygio - _batdau;

        // 5s cuoi thi bat den vang (bang lcd)
        if (troiqua >= (gioihan - 5000)) _p.vang(1);
        else _p.vang(0);

        if (troiqua >= gioihan) {
            _laxanh = !_laxanh;
            _batdau = baygio;
            capnhat_den();
        }
    }

    void bat() { _kichhoat = true; _batdau = millis(); _laxanh = true; capnhat_den(); }
    void tat() { _kichhoat = false; _p.tathet(); }
    bool dangchay() { return _kichhoat; }

private:
    dieu_khien_pin& _p; uint32_t _batdau; bool _kichhoat = false; bool _laxanh = true;
    void capnhat_den() { _p.xanh(_laxanh); _p.do_(!_laxanh); }
};

// 3. model_ket: ep den khi ket xe (A, B)
class model_ket {
public:
    model_ket(dieu_khien_pin& p, bool laxanh) : _p(p), _lax(laxanh) {}
    void ep(bool b) {
        _dangep = b;
        if (_dangep) { _p.xanh(_lax); _p.do_(!_lax); _p.vang(0); }
    }
    bool dangep() { return _dangep; }
    void huy() { _dangep = false; }
private:
    dieu_khien_pin& _p; bool _lax; bool _dangep = false;
};

// 4. model_thoang: giai phong (a, b)
class model_thoang {
public:
    void kichhoat() { _s = true; }
    bool cotinhieu() { return _s; }
    void xoa() { _s = false; }
private:
    bool _s = false;
};

// 5. doc_uart: bat lenh m1, m2, A, a, B, b
struct cmd { char loai = ' '; uint8_t val = 0; };
class doc_uart {
public:
    cmd doc() {
        cmd c;
        if (Serial.available()) {
            String s = Serial.readStringUntil('\n');
            s.trim();
            if (s.length() == 0) return c;

            if (s[0] == 'm') { c.loai = 'm'; c.val = s.substring(1).toInt(); }
            else if (s == "A") c.loai = 'A';
            else if (s == "B") c.loai = 'B';
            else if (s == "a") c.loai = 'a';
            else if (s == "b") c.loai = 'b';
        }
        return c;
    }
};