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
        delayMicroseconds(1);

        // --- Chuỗi khởi tạo MAX7219 ---
        _ghi_reg(REG_DISPLAY_TEST, 0x00);  // Tắt chế độ test
        _ghi_reg(REG_SHUTDOWN,     0x01);  // Chế độ hoạt động bình thường
        _ghi_reg(REG_DECODE_MODE,  0x03);  // BCD decode cho digit 0 và 1
        _ghi_reg(REG_SCAN_LIMIT,   0x01);  // Chỉ quét 2 digit (digit 0 & 1)
        _ghi_reg(REG_INTENSITY,    0x07);  // Độ sáng 50% (0x00–0x0F)
        xoa();
    }

    // Hiển thị số 0–99 với caching — không ghi SPI nếu số không đổi
    void hien_thi_so(uint8_t so) {
        if (so == _soHienThi) return;
        _soHienThi = so;

        uint8_t hangChuc   = so / 10;
        uint8_t hangDonVi  = so % 10;

        // Digit 0 (REG 0x01) = hàng đơn vị
        // Digit 1 (REG 0x02) = hàng chục (hiển thị trống nếu < 10)
        _ghi_reg(0x01, hangDonVi);
        _ghi_reg(0x02, (so < 10) ? KY_TU_TRONG : hangChuc);
    }

    // Tắt tất cả segment
    void xoa() {
        _soHienThi = 0xFF;
        _ghi_reg(0x01, KY_TU_TRONG);
        _ghi_reg(0x02, KY_TU_TRONG);
    }

    // Tắt nguồn MAX7219 (tiết kiệm điện khi không cần)
    void tat_nguon() { _ghi_reg(REG_SHUTDOWN, 0x00); }
    void bat_nguon() { _ghi_reg(REG_SHUTDOWN, 0x01); }

private:
    const uint8_t _pinClk, _pinDin, _pinCs;
    uint8_t       _soHienThi;

    // Địa chỉ thanh ghi MAX7219
    static constexpr uint8_t REG_DECODE_MODE  = 0x09;
    static constexpr uint8_t REG_INTENSITY    = 0x0A;
    static constexpr uint8_t REG_SCAN_LIMIT   = 0x0B;
    static constexpr uint8_t REG_SHUTDOWN     = 0x0C;
    static constexpr uint8_t REG_DISPLAY_TEST = 0x0F;

    // Ký tự "trống" trong chế độ BCD decode của MAX7219
    static constexpr uint8_t KY_TU_TRONG      = 0x0F;

    // Ghi 1 cặp (register, data) vào MAX7219
    void _ghi_reg(uint8_t reg, uint8_t data) {
        digitalWrite(_pinCs, LOW);
        _shift_out(reg);
        _shift_out(data);
        digitalWrite(_pinCs, HIGH);
        delayMicroseconds(1);   // tCS hold time
    }

    // Bit-bang SPI: MSB trước
    void _shift_out(uint8_t val) {
        for (int8_t i = 7; i >= 0; --i) {
            digitalWrite(_pinClk, LOW);
            digitalWrite(_pinDin, (val >> i) & 0x01 ? HIGH : LOW);
            digitalWrite(_pinClk, HIGH);
        }
    }
};