#pragma once
#include <Arduino.h>

class Pin_DieuKhien {
public:
    Pin_DieuKhien(uint8_t px, uint8_t pd, uint8_t pv) : _x(px), _d(pd), _v(pv) {}
    void batDau() { pinMode(_x, OUTPUT); pinMode(_d, OUTPUT); pinMode(_v, OUTPUT); tatHet(); }
    void denXanh(bool on) { digitalWrite(_x, on ? HIGH : LOW); }
    void denDo(bool on)   { digitalWrite(_d, on ? HIGH : LOW); }
    void denVang(bool on) { digitalWrite(_v, on ? HIGH : LOW); }
    void tatHet() { denXanh(0); denDo(0); denVang(0); }
private:
    uint8_t _x, _d, _v;
};

class Model_Timer {
public:
    explicit Model_Timer(Pin_DieuKhien& p) : _p(p) {}
    uint32_t layTG(uint8_t m) {
        const uint32_t t[] = {10, 15, 20, 25, 30};
        return (m <= 4) ? t[m] : t[0];
    }
    void Run_auto(uint8_t m) {
        if (!_act) return;
        uint32_t now = millis();
        uint32_t t_limit = layTG(m) * 1000;
        uint32_t elapsed = now - _start;

        if (elapsed >= (t_limit - 5000)) _p.denVang(1);
        else _p.denVang(0);

        if (elapsed >= t_limit) {
            _isX = !_isX;
            _start = now;
            _update();
        }
    }
    void Bat() { _act = true; _start = millis(); _isX = true; _update(); }
    void Tat() { _act = false; _p.tatHet(); }
    bool dangChay() { return _act; }
private:
    Pin_DieuKhien& _p; uint32_t _start; bool _act = false; bool _isX = true;
    void _update() { _p.denXanh(_isX); _p.denDo(!_isX); }
};

class Model_Ket {
public:
    Model_Ket(Pin_DieuKhien& p, bool x) : _p(p), _isX(x) {}
    void xuLy(bool b) {
        _run = b;
        if (_run) { _p.denXanh(_isX); _p.denDo(!_isX); _p.denVang(0); }
        else { _p.tatHet(); }
    }
    bool dangEp() { return _run; }
private:
    Pin_DieuKhien& _p; bool _isX; bool _run = false;
};

class Model_Thoang {
public:
    void capNhat(bool b) { if (b && !_h) _s = true; _h = b; if (!b) _s = false; }
    bool coTinHieu() { return _s; }
    void xoa() { _s = false; }
private:
    bool _h = false; bool _s = false;
};

struct Cmd { char k = ' '; uint8_t v = 0; };
class Doc_UART {
public:
    Cmd doc() {
        Cmd c;
        if (Serial.available()) {
            String s = Serial.readStringUntil('\n'); s.trim();
            int p = s.indexOf(':');
            if (p != -1) {
                String k = s.substring(0, p);
                c.v = s.substring(p + 1).toInt();
                c.k = (k == "MODE") ? 'M' : k[0];
            }
        }
        return c;
    }
};