#pragma once
#include <Arduino.h>

// 1. PIN_DIEUKHIEN
class Pin_DieuKhien {
public:
    Pin_DieuKhien(uint8_t Pin_xanh, uint8_t Pin_do, uint8_t Pin_vang)
        : _pinG(Pin_xanh), _pinR(Pin_do), _pinY(Pin_vang) {}

    void batdau() {
        pinMode(_pinG, OUTPUT);
        pinMode(_pinR, OUTPUT);
        pinMode(_pinY, OUTPUT);
        tathet();
    }

    void denXanh(bool on) { digitalWrite(_pinG, on ? HIGH : LOW); }
    void denDo(bool on)   { digitalWrite(_pinR, on ? HIGH : LOW); }
    void denVang(bool on) { digitalWrite(_pinY, on ? HIGH : LOW); }

    void tathet() {
        denXanh(0); // Lỗi cũ: viết thường denxanh(0)
        denDo(0);   // Lỗi cũ: viết thường dendo(0)
        denVang(0); // Lỗi cũ: viết thường denvang(0)
    }

private:
    uint8_t _pinG, _pinR, _pinY;
};

// 2. MODEL_TIMER
class Model_Timer {
public:
    // Sửa lỗi: _pin (private) chứ không phải Pin hay Pin_DieuKhien
    explicit Model_Timer(Pin_DieuKhien& pin) : _pin(pin) {}

    uint32_t bangtimer(uint8_t mode) {
        const uint32_t time_mode[] = {10, 15, 20, 25, 30};
        return (mode <= 4) ? time_mode[mode] : time_mode[0];
    }

    void Run_auto(uint8_t mode) {
        if (!dangChay()) return; // Lỗi cũ: Pin.dangchay() - gọi hàm của chính lớp này

        uint32_t time_now = millis();
        uint32_t t_mode = bangtimer(mode) * 1000; 
        uint32_t time_datroi = time_now - _time_start;

        if (time_datroi >= (t_mode - 5000)) {
            _pin.denVang(1); // Lỗi cũ: denvang(1) viết thường
        } else {
            _pin.denVang(0);
        }

        if (time_datroi >= t_mode) {
            _isXanh = !_isXanh; // Đổi trạng thái pha
            _time_start = time_now;
            updatelight();
        }
    }

    void Bat() { 
        _dangchay = true; 
        _time_start = millis(); 
        _isXanh = true; 
        updatelight(); 
    }
    
    void Tat() { _dangchay = false; _pin.tathet(); }
    bool dangChay() { return _dangchay; }

private:
    Pin_DieuKhien& _pin;
    uint32_t _time_start = 0;
    bool _dangchay = false;
    bool _isXanh = true;

    void updatelight() {
        _pin.denXanh(_isXanh);
        _pin.denDo(!_isXanh);
    }
};

// 3. MODEL_KET
class Model_Ket {
public:
    // Lỗi cũ: Truyền vào DieuKhienPin (sai tên lớp) -> Sửa thành Pin_DieuKhien
    explicit Model_Ket(Pin_DieuKhien& pin, bool epXanh) 
        : _pin(pin), _epXanh(epXanh) {}

    void xuLy(bool bat) {
        if (bat == _dangEp) return;
        _dangEp = bat;

        if (_dangEp) {
            _pin.denXanh(_epXanh);
            _pin.denDo(!_epXanh);
            _pin.denVang(0);
        } else {
            _pin.tathet(); // Lỗi cũ: tatHet() viết hoa chữ H
        }
    }

    bool dangEp() { return _dangEp; }

private:
    Pin_DieuKhien& _pin;
    bool _epXanh;
    bool _dangEp = false;
};

// 4. MODEL_THOANG (Giữ nguyên - code này của bạn đã ổn)
class Model_Thoang {
public:
    void capNhat(bool tinHieu) {
        if (tinHieu && !_dangGiu) _coLenh = true;
        _dangGiu = tinHieu;
        if (!tinHieu) _coLenh = false;
    }
    bool coTinHieu() { return _coLenh; }
    void xoaLenh() { _coLenh = false; }
private:
    bool _dangGiu = false;
    bool _coLenh = false;
};

// 5. DOC_UART (Giữ nguyên)
struct DuLieuLenh { char kyTu = ' '; uint8_t giaTri = 0; };

class Doc_UART {
public:
    DuLieuLenh doc() {
        DuLieuLenh d;
        if (Serial.available()) {
            String s = Serial.readStringUntil('\n');
            s.trim();
            int tach = s.indexOf(':');
            if (tach != -1) {
                String key = s.substring(0, tach);
                d.giaTri = s.substring(tach + 1).toInt();
                d.kyTu = (key == "MODE") ? 'M' : key[0];
            }
        }
        return d;
    }
};