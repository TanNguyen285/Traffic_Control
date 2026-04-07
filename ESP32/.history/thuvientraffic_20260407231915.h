#pragma once
#include <Arduino.h>

class DieuKhienPin {
public:
    Pin_DieuKhien(uint8_t Pin_xanh, uint8_t Pin_do, uint8_t Pin_vang)
        : Pin_g(Pin_xanh), Pin_r(Pin_do), Pin_y(Pin_vang) {}

    void batdau() {
        pinMode(Pin_g, OUTPUT);
        pinMode(Pin_r,   OUTPUT);
        pinMode(Pin_y, OUTPUT);
        tathet();
    }

    void denXanh(bool on) { digitalWrite(Pin_g, on ? HIGH : LOW); }
    void denDo(bool on)   { digitalWrite(Pin_r,   on ? HIGH : LOW); }
    void denVang(bool on) { digitalWrite(Pin_y, on ? HIGH : LOW); }

    void tathet() {
        denXanh(0);
        dendo(0);
        denVang(0);
    }

private:
    uint8_t Pin_g, Pin_r, Pin_y;
};
// ============================================================
// 2. MODEL_TIMER: Quản lý đếm ngược và chu kỳ Mode
// ============================================================
class Model_Timer {
public:
    explicit Model_Timer(DieuKhienPin& pin) : _pin(pin) {}

    // Trả về thời gian tổng của Mode (giây)
    uint32_t bangtimer(uint8_t mode) {
        const uint32_t time_mode[] = {10, 15, 20, 25, 30}; // Giây (m0/,m1,m2,m3,m4)
        return (mode <= 4) ? time_mode[mode] : time_mode[0];
    }

    void Run_auto(uint8_t mode) {
        if (!_dangKichHoat) return;

        uint32_t time_now = millis();
        uint32_t time_mode = bangtimer(mode) * 1000; // Đổi sang ms
        uint32_t time_datroi= time_now - time_start;

        // Logic đèn vàng (bảng báo): Sáng 5s cuối trước khi đổi pha
        if (time_datroi >= (time_mode - 5000)) {
            (1);
        } else {
            _pin.denVang(0);
        }

        // Chuyển pha Xanh <-> Đỏ
        if (time_datroi >= time_mode) {
            denxanh = !denxanh;
            time_start = time_now;
            _capNhatDen();
        }
    }

    void bat() { 
        _dangKichHoat = true; 
        time_start = millis(); 
        denxanh = true; 
        _capNhatDen(); 
    }
    
    void tat() { _dangKichHoat = false; _pin.tatHet(); }
    bool dangChay() { return _dangKichHoat; }

private:
    DieuKhienPin& _pin;
    uint32_t time_start = 0;
    bool _dangKichHoat = false;
    bool denxanh = true;

    void _capNhatDen() {
        _pin.denXanh(denxanh);
        _pin.denDo(!denxanh );
    }
};

// ============================================================
// 3. MODEL_KET (Trạm A/B): Ép đèn khi kẹt xe
// ============================================================
class Model_Ket {
public:
    explicit Model_Ket(DieuKhienPin& pin, bool epXanh) 
        : _pin(pin), _epXanh(epXanh) {}

    void xuLy(bool bat) {
        if (bat == _dangEp) return;
        _dangEp = bat;

        if (_dangEp) {
            _pin.denXanh(_epXanh);
            _pin.denDo(!_epXanh);
            _pin.denVang(0);
        } else {
            _pin.tatHet();
        }
    }

    bool dangEp() { return _dangEp; }

private:
    DieuKhienPin& _pin;
    bool _epXanh;
    bool _dangEp = false;
};

// ============================================================
// 4. MODEL_THOANG (Trạm a/b): Tín hiệu giải phóng
// ============================================================
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

// ============================================================
// 5. DOC_UART: Nhận lệnh từ Raspberry Pi
// ============================================================
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