#include "hethong.h"

// Thiet lap chan cam
dieu_khien_pin den(2, 3, 4);

nhan_lenh_uart  uart;
bo_dem_gio      dong_ho(den);
tram_bi_ket     tram_a(den, true);  // A: Ep xanh
tram_bi_ket     tram_b(den, false); // B: Ep do
tram_thong_thoang thong_a, thong_b;

uint8_t che_do_hien_tai = 1;

void setup() {
    Serial.begin(115200);
    den.bat_dau();
}

void loop() {
    tin_nhan lenh = uart.doc_tin_nhan();

    if (lenh.chu_cai != ' ') {
        if (lenh.chu_cai == 'm') { 
            che_do_hien_tai = lenh.con_so; 
            tram_a.xa_ket(); tram_b.xa_ket(); 
            dong_ho.bat(); 
        }
        else if (lenh.chu_cai == 'A') { tram_a.ep_dung_yen(true);  tram_b.xa_ket(); }
        else if (lenh.chu_cai == 'B') { tram_b.ep_dung_yen(true);  tram_a.xa_ket(); }
        else if (lenh.chu_cai == 'a') { thong_a.co_tin_hieu();     tram_a.xa_ket(); }
        else if (lenh.chu_cai == 'b') { thong_b.co_tin_hieu();     tram_b.xa_ket(); }
    }

    // Neu ca 2 tram khong bi ket thi moi chay tu dong
    if (tram_a.co_dang_bi_ket_khong() == false && tram_b.co_dang_bi_ket_khong() == false) {
        dong_ho.chay_tu_dong(che_do_hien_tai);
    }

    // Kiem tra tram A thong chua de lam viec khac
    if (thong_a.check_xem_thong_chua()) {
        // Xu ly xong thi bao xong
        thong_a.xong_roi();
    }
}