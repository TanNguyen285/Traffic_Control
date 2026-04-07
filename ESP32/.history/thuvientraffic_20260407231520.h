#pragma once
#include <Arduino.h>

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
        if (daTroiQua >= (time_mode - 5000)) {
            _pin.denVang(1);
        } else {
            _pin.denVang(0);
        }

        // Chuyển pha Xanh <-> Đỏ
        if (daTroiQua >= time_mode) {
            _laPhaXanh = !_laPhaXanh;
            _tgBatDau = time_now;
            _capNhatDen();
        }
    }

    void bat() { 
        _dangKichHoat = true; 
        _tgBatDau = millis(); 
        _laPhaXanh = true; 
        _capNhatDen(); 
    }
    
    void tat() { _dangKichHoat = false; _pin.tatHet(); }
    bool dangChay() { return _dangKichHoat; }

private:
    DieuKhienPin& _pin;
    uint32_t _tgBatDau = 0;
    bool _dangKichHoat = false;
    bool _laPhaXanh = true;

    void _capNhatDen() {
        _pin.denXanh(_laPhaXanh);
        _pin.denDo(!_laPhaXanh);
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