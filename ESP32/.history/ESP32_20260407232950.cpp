#include "hethong.h"

// khai bao (chan xanh, do, vang)
dieu_khien_pin pin(2, 3, 4);

doc_uart uart;
model_timer timer(pin);
model_ket keta(pin, true);  // A la ep xanh
model_ket ketb(pin, false); // B la ep do
model_thoang thoanga, thoangb;

uint8_t mode_ht = 1;

void setup() {
    Serial.begin(115200);
    pin.batdau();
}

void loop() {
    cmd lenh = uart.doc();

    if (lenh.loai != ' ') {
        if (lenh.loai == 'm') { 
            mode_ht = lenh.val; 
            keta.huy(); ketb.huy(); 
            timer.bat(); 
        }
        else if (lenh.loai == 'A') { keta.ep(true); ketb.huy(); }
        else if (lenh.loai == 'B') { ketb.ep(true); keta.huy(); }
        else if (lenh.loai == 'a') { thoanga.kichhoat(); keta.huy(); }
        else if (lenh.loai == 'b') { thoangb.kichhoat(); ketb.huy(); }
    }

    // neu khong bi ket thi chay tu dong
    if (!keta.dangep() && !ketb.dangep()) {
        timer.chay_auto(mode_ht);
    }

    // xu ly tin hieu thoang (neu can)
    if (thoanga.cotinhieu()) {
        thoanga.xoa();
    }
}