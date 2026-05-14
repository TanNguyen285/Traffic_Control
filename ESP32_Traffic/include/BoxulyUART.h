#pragma once
#include <Arduino.h>
#include "kieudulieu.h"
#include "Cauhinhchan.h"

class BoXuLyUART {
public:
    BoXuLyUART()
        : _hSerial(nullptr), _dangDocMode(false), _coLenhMoi(false), _lenhVuaNhan{} {}

    // 1. Sửa hàm này: Bỏ tham số QueueHandle_t
    void khoi_dong(HardwareSerial& serial) {
        _hSerial = &serial;
        
        if (&serial == &Serial) {
            serial.begin(115200);
        } else {
            serial.begin(CauHinhUART::BAUD_RATE, SERIAL_8N1, Pin::UART_RX, Pin::UART_TX);
        }
    }

    // 2. Thêm hàm này để Main có thể kiểm tra xem có lệnh mới không
    bool co_lenh(LenhNhan& lenh) {
        if (_coLenhMoi) {
            lenh = _lenhVuaNhan;
            _coLenhMoi = false; // Reset cờ sau khi lấy lệnh ra
            return true;
        }
        return false;
    }

    void cap_nhat() {
        if (!_hSerial) return;
        while (_hSerial->available()) {
            _xu_ly_ky_tu((char)_hSerial->read());
        }
    }

    void gui_ve_pi(const char* chuoi) {
        if (_hSerial) {
            _hSerial->println(chuoi);
            Serial.printf("[TX] Gui: '%s'\n", chuoi);
        }
    }

private:
    HardwareSerial* _hSerial;
    bool            _dangDocMode;  
    bool            _coLenhMoi;    // Cờ báo hiệu có lệnh mới
    LenhNhan        _lenhVuaNhan;  // Biến lưu trữ lệnh vừa nhận

    void _xu_ly_ky_tu(char c) {
        if (_dangDocMode) {
            _dangDocMode = false;
            if (c >= '0' && c <= '4') {
                // Thay vì gửi vào Queue, ta lưu trực tiếp vào biến thành viên
                _lenhVuaNhan = { LoaiLenh::MODE, (uint8_t)(c - '0') };
                _coLenhMoi = true;
                Serial.printf("[RX] Nhan lenh: MODE (m%c)\n", c);
            }
            return;
        }

        switch (c) {
            case 'm':
                _dangDocMode = true;
                break;
            case 'A': 
                _lenhVuaNhan = { LoaiLenh::BAT_UU_TIEN, 0 };
                _coLenhMoi = true;
                Serial.printf("[RX] Nhan lenh: BAT_UU_TIEN Node A\n");
                break;
            case 'B': 
                _lenhVuaNhan = { LoaiLenh::BAT_UU_TIEN, 1 };
                _coLenhMoi = true;
                Serial.printf("[RX] Nhan lenh: BAT_UU_TIEN Node B\n");
                break;
            case 'a': 
                _lenhVuaNhan = { LoaiLenh::TAT_UU_TIEN, 0 };
                _coLenhMoi = true;
                Serial.printf("[RX] Nhan lenh: TAT_UU_TIEN Node A\n");
                break;
            case 'b': 
                _lenhVuaNhan = { LoaiLenh::TAT_UU_TIEN, 1 };
                _coLenhMoi = true;
                Serial.printf("[RX] Nhan lenh: TAT_UU_TIEN Node B\n");
                break;
            case 'S':
            case 's': 
                _lenhVuaNhan = { LoaiLenh::BAT_DAU, 0 };
                _coLenhMoi = true;
                Serial.println("[RX] Nhan lenh UART: BAT DAU HE THONG!");
                break;
            default:
                break;
        }
    }
};