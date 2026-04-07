#pragma once
#include <Arduino.h>

// ============================================================
// 1. NGO_RA: Điều khiển các chân vật lý
// ============================================================
class NgoRa {
public:
    NgoRa(uint8_t pXanh, uint8_t pDo, uint8_t pLcd)
        : _x(pXanh), _d(pDo), _l(pLcd) {}

    void dau() {
        pinMode(_x, OUTPUT); pinMode(_d, OUTPUT); pinMode(_l, OUTPUT);
        off();
    }

    void xanh(bool on) { digitalWrite(_x, on ? HIGH : LOW); }
    void do_(bool on)  { digitalWrite(_d, on ? HIGH : LOW); }
    void lcd(bool on)  { digitalWrite(_l, on ? HIGH : LOW); } // Bật bảng LCD báo hiệu

    void off() { xanh(0); do_(0); lcd(0); }

private:
    uint8_t _x, _d, _l;
};

// ============================================================
// 2. EP_LENH: Ép xanh (A) hoặc Đỏ (B)
// ============================================================
class EpLenh {
public:
    explicit EpLenh(NgoRa& hw, bool laXanh) : _hw(hw), _isX(laXanh) {}

    void chuyen(bool bat) {
        if (bat == _run) return;
        _run = bat;
        if (_run) {
            _hw.xanh(_isX); _hw.do_(!_isX); _hw.lcd(0);
        } else {
            _hw.off();
        }
    }
    bool dangChay() { return _run; }

private:
    NgoRa& _hw; bool _isX; bool _run = false;
};

// ============================================================
// 3. TU_DONG: Chạy Mode M0-M4, có báo hiệu LCD 5s cuối
// ============================================================
class TuDong {
public:
    enum Pha { XANH, DO };
    static constexpr uint32_t TG_LCD = 5000; // 5 giây hiện bảng báo

    explicit TuDong(NgoRa& hw) : _hw(hw) {}

    void chay(uint8_t m) {
        if (!_act) return;
        
        uint32_t now = millis();
        uint32_t tgGoc = _getTG(m);
        uint32_t troiQua = now - _start;

        // Logic điều khiển LCD: Bật khi pha sắp kết thúc (còn 5s)
        if (tgGoc > TG_LCD && troiQua >= (tgGoc - TG_LCD)) {
            _hw.lcd(1);
        } else {
            _hw.lcd(0);
        }

        // Chuyển pha
        if (troiQua >= tgGoc) {
            _p = (_p == XANH) ? DO : XANH;
            _start = now;
            _updateHW();
        }
    }

    void bat() { _act = 1; _p = XANH; _start = millis(); _updateHW(); }
    void tat() { _act = 0; _hw.off(); }
    bool dangAct() { return _act; }

private:
    NgoRa& _hw; bool _act = 0; Pha _p = XANH; uint32_t _start = 0;

    uint32_t _getTG(uint8_t m) {
        const uint32_t t[] = {10000, 15000, 20000, 25000, 30000};
        return (m <= 4) ? t[m] : t[0];
    }

    void _updateHW() {
        _hw.xanh(_p == XANH);
        _hw.do_(_p == DO);
    }
};

// ============================================================
// 4. MO_LENH: Tín hiệu giải phóng (a, b)
// ============================================================
class MoLenh {
public:
    void update(bool b) {
        if (b && !_hold) _sig = 1;
        _hold = b;
        if (!b) _sig = 0;
    }
    bool check() { return _sig; }
    void clear() { _sig = 0; }
private:
    bool _hold = 0; bool _sig = 0;
};

// ============================================================
// 5. UART: Đọc lệnh từ Pi
// ============================================================
struct Cmd { char k = ' '; uint8_t v = 0; };

class ReadUart {
public:
    Cmd get() {
        Cmd c;
        if (Serial.available()) {
            String s = Serial.readStringUntil('\n');
            s.trim();
            int pos = s.indexOf(':');
            if (pos != -1) {
                String key = s.substring(0, pos);
                c.v = s.substring(pos + 1).toInt();
                c.k = (key == "MODE") ? 'M' : key[0];
            }
        }
        return c;
    }
};