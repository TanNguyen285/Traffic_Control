#pragma once
#include <Arduino.h>
#include "Cauhinhchan.h"

// ============================================================
// Man7Doan.h — Driver MAX7219 (SPI phần mềm)
//   Điều khiển 2 LED 7-đoạn hiển thị đếm ngược 00–99.
//   1 chip MAX7219 quản lý cả 2 digit (scan limit = 0x01).
// ============================================================
class Led7Doan {
public:
    Led7Doan(uint8_t pinClk, uint8_t pinDin, uint8_t pinCs)
        : _pinClk(pinClk), _pinDin(pinDin), _pinCs(pinCs),
          _soHienThi(0xFF) {}   // 0xFF = chưa có giá trị → buộc ghi lần đầu

    void khoi_dong() {
pinMode(_pinClk, OUTPUT);
        pinMode(_pinDin, OUTPUT);
        pinMode(_pinCs,  OUTPUT);
        digitalWrite(_pinCs, HIGH);
        xoa();
    }

    // Hiển thị số 0–99 với caching — không ghi SPI nếu số không đổi
void hien_thi_so(uint8_t so) {
        if (so == _soHienThi) return;
        _soHienThi = so;

        if (so > 99) so = 99;
        uint8_t hangChuc  = so / 10;
        uint8_t hangDonVi = so % 10;

        digitalWrite(_pinCs, LOW); // Bắt đầu nạp dữ liệu

        // Gửi 2 byte cho 2 chip 595 nối tầng
        // Nếu số bị hiện ngược vị trí, huynh hãy đổi chỗ 2 dòng dưới này
        _gui_du_lieu(_maLed[hangDonVi]); 
        _gui_du_lieu(so < 10 ? 0xFF : _maLed[hangChuc]); // Tắt số 0 ở hàng chục

        digitalWrite(_pinCs, HIGH); // Chốt và hiển thị
    }

    // Tắt tất cả segment
void xoa() {
        _soHienThi = 0xFF;
        digitalWrite(_pinCs, LOW);
        _gui_du_lieu(0xFF); // Tắt tất cả các thanh (Anode chung)
        _gui_du_lieu(0xFF);
        digitalWrite(_pinCs, HIGH);
    }

private:
    const uint8_t _pinClk, _pinDin, _pinCs;
    uint8_t _soHienThi;

    // Bảng mã LED 7 đoạn (Cực dương chung - Common Anode)
    const uint8_t _maLed[10] = {
        0xC0, 0xF9, 0xA4, 0xB0, 0x99, 0x92, 0x82, 0xF8, 0x80, 0x90
    };

    void _gui_du_lieu(uint8_t data) {
        // Gửi dữ liệu chậm rãi để chip 595 nhận diện chính xác[cite: 7]
        shiftOut(_pinDin, _pinClk, MSBFIRST, data);
    }
};