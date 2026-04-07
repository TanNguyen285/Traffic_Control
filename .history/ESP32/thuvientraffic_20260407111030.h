#ifndef TRAFFIC_STATION_H
#define TRAFFIC_STATION_H

#include <Arduino.h>

// Định nghĩa các Mode hệ thống
enum SystemMode { MODE_M1, MODE_M2, MODE_M3, MODE_M4 };

class TrafficStation {
private:
    char _stationID;
    int _pinGreen, _pinRed, _pinBuzzer;
    SystemMode _currentMode;
    
    // Các thông số thời gian mặc định (có thể thay đổi theo Mode)
    int _timeG = 150; // Giây
    int _timeR = 150;

public:
    // Constructor: Khởi tạo chân và ID trạm
    TrafficStation(char id, int green, int red, int buzzer) {
        _stationID = id;
        _pinGreen = green;
        _pinRed = red;
        _pinBuzzer = buzzer;
        _currentMode = MODE_M1;
    }

    void init() {
        pinMode(_pinGreen, OUTPUT);
        pinMode(_pinRed, OUTPUT);
        pinMode(_pinBuzzer, OUTPUT);
        allLedsOff();
    }

    void allLedsOff() {
        digitalWrite(_pinGreen, LOW);
        digitalWrite(_pinRed, LOW);
        digitalWrite(_pinBuzzer, LOW);
    }

    // Xử lý logic Đèn Xanh (Nhóm biến A, a)
    void runGreenPhase() {
        Serial.printf("[Trạm %c] Đèn XANH bắt đầu...\n", _stationID);
        digitalWrite(_pinGreen, HIGH);
        digitalWrite(_pinRed, LOW);

        // Logic giảm thời gian theo Mode (ví dụ time_g - 2)
        int actualTime = (_currentMode == MODE_M2) ? (_timeG - 2) : _timeG;
        
        // Chờ đến khi còn 5s cuối (giả lập hoặc chờ biến 'a')
        vTaskDelay(pdMS_TO_TICKS((actualTime - 5) * 1000));
        
        triggerWarning();
        digitalWrite(_pinGreen, LOW);
    }

    // Xử lý logic Đèn Đỏ (Nhóm biến B, b)
    void runRedPhase() {
        Serial.printf("[Trạm %c] Đèn ĐỎ bắt đầu...\n", _stationID);
        digitalWrite(_pinRed, HIGH);
        digitalWrite(_pinGreen, LOW);
        
        // Đèn đỏ thường đợi tín hiệu 'b' bên ngoài, 
        // Sau đó mới gọi triggerWarning trước khi kết thúc
    }

    void triggerWarning() {
        Serial.println("-> Cảnh báo 5 giây cuối!");
        for (int i = 0; i < 5; i++) {
            digitalWrite(_pinBuzzer, HIGH);
            vTaskDelay(pdMS_TO_TICKS(500));
            digitalWrite(_pinBuzzer, LOW);
            vTaskDelay(pdMS_TO_TICKS(500));
        }
    }

    void setMode(SystemMode m) { _currentMode = m; }
    char getID() { return _stationID; }
};

#endif