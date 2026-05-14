#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>


#include "Kieudulieu.h"          
#include "Cauhinhchan.h"         
#include "DenGiaoThong.h"        
#include "Led7Doan.h"            
#include "BoXuLyUART.h"
#include "BoDieuKhienNgaTu.h"

// ============================================================
// main.cpp — Entry point, FreeRTOS task definitions
//
//   Task layout:
//     taskDocUART       (Core 0, Pri 2) — poll UART, push to queue
//     taskXuLyCapNhat   (Core 1, Pri 1) — pop queue + run state machine
//
//   Tất cả blocking = vTaskDelay().
// ============================================================

// ------------------------------------------------------------
// Đối tượng toàn cục (static → tránh heap allocation muộn)
// ------------------------------------------------------------


static DenGiaoThong   denGiaoThong(Pin::DEN_XANH, Pin::DEN_VANG, Pin::DEN_DO);
static Led7Doan       led7Doan(Pin::MAX7219_CLK, Pin::MAX7219_DIN, Pin::MAX7219_CS);
static BoXuLyUART     boUART;
static BoDieuKhienNgaTu*  boDieuKhien = nullptr;   // Khởi tạo sau khi biết nodeId

// ------------------------------------------------------------
// Đọc Node ID từ GPIO (LOW = Node A, HIGH = Node B)
// ------------------------------------------------------------
static NodeID doc_node_id() {
    pinMode(Pin::NODE_ID, INPUT_PULLUP);
    vTaskDelay(pdMS_TO_TICKS(10));    // Chờ điện áp pull-up ổn định
    return (digitalRead(Pin::NODE_ID) == HIGH)
           ? NodeID::NODE_A
           : NodeID::NODE_B;
}

// ------------------------------------------------------------
// Task 1: Đọc UART và đẩy lệnh vào hàng đợi
//   Core 0, ưu tiên cao hơn để không bỏ sót byte UART
// ------------------------------------------------------------
static void Doc_UART(void* tham_so) {
    Serial.println("[TASK] Doc_UART khoi hanh tren Core 0");
    for (;;) {
        boUART.cap_nhat();
        
        // Thêm nhịp đập (heartbeat) để biết Task không chết
        if (millis() % 5000 == 0) {
            Serial.println("[HEARTBEAT] Core 0 van dang nghe UART...");
            vTaskDelay(pdMS_TO_TICKS(1)); // Tránh in trùng lặp trong cùng 1ms
        }
        
        vTaskDelay(pdMS_TO_TICKS(5)); 
    }
}

// ------------------------------------------------------------
// Task 2: Xử lý lệnh từ queue + cập nhật state machine
//   Core 1, chạy mỗi 10ms
// ------------------------------------------------------------
static void XuLyCapNhat(void* tham_so) {
    LenhNhan lenh;
    for (;;) {
        if (boUART.co_lenh(lenh)) { 
            if (boDieuKhien) {
                boDieuKhien->nhan_lenh(lenh);
            }
        }
        if (boDieuKhien) {
            boDieuKhien->cap_nhat((uint32_t)millis());
        }

        // BẮT BUỘC: Phải có delay để nhường Core 1 cho các tác vụ hệ thống (WiFi/TCP)
        vTaskDelay(pdMS_TO_TICKS(10)); 
    }
}


// ------------------------------------------------------------
// setup()
// ------------------------------------------------------------
void setup() {
    // Serial0 chỉ dùng để debug 
    Serial.begin(115200);
    Serial.println();
    Serial.println("=== He thong dieu khien den giao thong ===");



    // 2. Xác định Node ID
    NodeID nodeId = doc_node_id();
    Serial.printf("[BOOT] Node ID: %s\n",nodeId == NodeID::NODE_A ? "A (bat dau XANH)" : "B (bat dau DO)");

    // 3. Khởi tạo phần cứng
    denGiaoThong.khoi_dong();
    led7Doan.khoi_dong();
    boUART.khoi_dong(Serial2);

    // 4. Khởi tạo state machine
    boDieuKhien = new BoDieuKhienNgaTu(nodeId, denGiaoThong, led7Doan, boUART);
    boDieuKhien->khoi_dong();

    // 5. Tạo FreeRTOS tasks
    BaseType_t ok1 = xTaskCreatePinnedToCore(
        Doc_UART,
        "DocUART",
        2048,           // Stack 2KB — đủ cho UART polling đơn giản
        nullptr,
        2,              // Priority 2 (cao hơn task state machine)
        nullptr,
        0               // Core 0
    );

    BaseType_t ok2 = xTaskCreatePinnedToCore(
        XuLyCapNhat,
        "XuLyCapNhat",
        4096,           // Stack 4KB — state machine + SPI + UART send
        nullptr,
        1,              // Priority 1
        nullptr,
        1               // Core 1
    );

    if (ok1 != pdPASS || ok2 != pdPASS) {
        Serial.println("[FATAL] Khong tao duoc task! Restarting...");
        ESP.restart();
    }

    Serial.println("[BOOT] San sang. Nhan nut GPIO13 de bat dau...");
}

// ------------------------------------------------------------
// loop() Nhường hoàn toàn cho FreeRTOS scheduler.
// ------------------------------------------------------------
void loop() {
    vTaskDelay(portMAX_DELAY);
}