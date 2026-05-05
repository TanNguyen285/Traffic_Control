#pragma once
#include <Arduino.h>
#include "Cauhinhchan.h"

// ============================================================
// DenGiaoThong.h — Điều khiển 3 đèn LED giao thông (Xanh/Vàng/Đỏ)
// ============================================================
class DenGiaoThong {
public:
    DenGiaoThong(uint8_t pinXanh, uint8_t pinVang, uint8_t pinDo)
        : _pinXanh(pinXanh), _pinVang(pinVang), _pinDo(pinDo) {}

    void khoi_dong() {
        pinMode(_pinXanh, OUTPUT);
        pinMode(_pinVang, OUTPUT);
        pinMode(_pinDo,   OUTPUT);
        tat_tat_ca();
    }

    void bat_xanh() {
        digitalWrite(_pinXanh, HIGH);
        digitalWrite(_pinVang, LOW);
        digitalWrite(_pinDo,   LOW);
    }

    void bat_vang() {
        digitalWrite(_pinXanh, LOW);
        digitalWrite(_pinVang, HIGH);
        digitalWrite(_pinDo,   LOW);
    }

    void bat_do() {
        digitalWrite(_pinXanh, LOW);
        digitalWrite(_pinVang, LOW);
        digitalWrite(_pinDo,   HIGH);
    }

    void tat_tat_ca() {
        digitalWrite(_pinXanh, LOW);
        digitalWrite(_pinVang, LOW);
        digitalWrite(_pinDo,   LOW);
    }

private:
    const uint8_t _pinXanh, _pinVang, _pinDo;
};