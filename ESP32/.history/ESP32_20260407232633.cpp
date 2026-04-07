#include "HeThongGiaoThong.h"

// Khởi tạo đối tượng điều khiển Pin (Xanh: 2, Đỏ: 3, Vàng: 4)
Pin_DieuKhien led(2, 3, 4);

// Khởi tạo các Model chức năng
Doc_UART    uart;
Model_Timer mTimer(led);
Model_Ket   ketA(led, true);  // Trạm A: Ép Xanh
Model_Ket   ketB(led, false); // Trạm B: Ép Đỏ
Model_Thoang thoangA, thoangB; 

uint8_t modeHienTai = 0;

void setup() {
    Serial.begin(115200);
    led.batDau(); 
}

void loop() {
    // 1. Nhận và phân loại lệnh UART
    Cmd lenh = uart.doc();
    if (lenh.k != ' ') {
        switch (lenh.k) {
            case 'M': modeHienTai = lenh.v; mTimer.Bat(); break;
            case 'A': ketA.xuLy(lenh.v); break;
            case 'B': ketB.xuLy(lenh.v); break;
            case 'a': thoangA.capNhat(lenh.v); break;
            case 'b': thoangB.capNhat(lenh.v); break;
        }
    }

    // 2. Logic vận hành hệ thống
    // Chỉ chạy tự động khi cả 2 trạm không bị ép (A=0 và B=0)
    if (!ketA.dangEp() && !ketB.dangEp()) {
        mTimer.Run_auto(modeHienTai);
    }

    // 3. Xử lý các tín hiệu giải phóng (a, b) nếu cần
    if (thoangA.coTinHieu()) {
        // Logic khi trạm a thoáng...
        thoangA.xoa();
    }
}