#pragma once
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include "kieudulieu.h"
#include "Cauhinhchan.h"

// ============================================================
// BoXuLyUART.h — UART Event-driven với FreeRTOS Queue
//
//   Luồng xử lý:
//     taskDocUART  →  cap_nhat()  →  _xu_ly_ky_tu()  →  xQueueSend()
//                                                           ↓
//     taskXuLyCapNhat  ←  xQueueReceive()  ←  [Queue<LenhNhan>]
//
//   Định dạng lệnh từ Pi:
//     "m0" .. "m4"  →  LoaiLenh::MODE,      giaTri = 0..4
//     'A'           →  LoaiLenh::BAT_UU_TIEN, giaTri = 0 (Node A)
//     'B'           →  LoaiLenh::BAT_UU_TIEN, giaTri = 1 (Node B)
//     'a'           →  LoaiLenh::TAT_UU_TIEN, giaTri = 0 (Node A)
//     'b'           →  LoaiLenh::TAT_UU_TIEN, giaTri = 1 (Node B)
// ============================================================
class BoXuLyUART {
public:
    BoXuLyUART()
        : _hSerial(nullptr), _Hangdoilenh(nullptr), _dangDocMode(false) {}

    // Khởi tạo cổng UART và liên kết với hàng đợi lệnh
    void khoi_dong(HardwareSerial& serial, QueueHandle_t queue) {
        _hSerial = &serial;
        _Hangdoilenh  = queue;
        serial.begin(CauHinhUART::BAUD_RATE, SERIAL_8N1, Pin::UART_RX, Pin::UART_TX);
    }

    // Đọc tất cả byte có sẵn trong UART buffer — gọi trong taskDocUART
    void cap_nhat() {
        if (!_hSerial || !_Hangdoilenh) return;
        while (_hSerial->available()) {
            _xu_ly_ky_tu((char)_hSerial->read());
        }
    }

    // Gửi chuỗi về Raspberry Pi (kết thúc bằng '\n')
    void gui_ve_pi(const char* chuoi) {
        if (_hSerial) {
            _hSerial->println(chuoi);
            Serial.printf("[TX] Gui: '%s'\n", chuoi);  // Echo local
        }
    }

private:
    HardwareSerial* _hSerial;
    QueueHandle_t   _Hangdoilenh;
    bool            _dangDocMode;   // true khi vừa đọc 'm', chờ ký tự số tiếp theo

    // Máy trạng thái parser đơn giản: nhận từng byte, nhận diện lệnh hợp lệ
    void _xu_ly_ky_tu(char c) {
        // ---- Trạng thái đang đọc "m" + số ----
        if (_dangDocMode) {
            _dangDocMode = false;
            if (c >= '0' && c <= '4') {
                LenhNhan lenh = { LoaiLenh::MODE, (uint8_t)(c - '0') };
                xQueueSend(_Hangdoilenh, &lenh, 0);  // Non-blocking: bỏ qua nếu queue đầy
                Serial.printf("[RX] Nhan lenh: MODE (m%c) | Che do: %u\n", c, (uint8_t)(c - '0'));
            }
            // Ký tự không hợp lệ sau 'm' → bỏ qua cả hai
            return;
        }

        // ---- Xử lý ký tự đơn ----
        switch (c) {
            case 'm':
                _dangDocMode = true;
                break;
            case 'A': {
                LenhNhan lenh = { LoaiLenh::BAT_UU_TIEN, 0 };
                xQueueSendToFront(_Hangdoilenh, &lenh, 0);
                Serial.printf("[RX] Nhan lenh: BAT_UU_TIEN Node A\n");
                break;
            }
            case 'B': {
                LenhNhan lenh = { LoaiLenh::BAT_UU_TIEN, 1 };
                xQueueSendToFront(_Hangdoilenh, &lenh, 0);
                Serial.printf("[RX] Nhan lenh: BAT_UU_TIEN Node B\n");
                break;
            }
            case 'a': {
                LenhNhan lenh = { LoaiLenh::TAT_UU_TIEN, 0 };
                xQueueSendToFront(_Hangdoilenh, &lenh, 0);
                Serial.printf("[RX] Nhan lenh: TAT_UU_TIEN Node A\n");
                break;
            }
            case 'b': {
                LenhNhan lenh = { LoaiLenh::TAT_UU_TIEN, 1 };
                xQueueSendToFront(_Hangdoilenh, &lenh, 0);
                Serial.printf("[RX] Nhan lenh: TAT_UU_TIEN Node B\n");
                break;
            }
            default:
                // Bỏ qua: '\n', '\r', khoảng trắng, ký tự lạ
                break;
        }
    }
};