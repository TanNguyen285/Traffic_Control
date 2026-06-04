#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include "ssd1306_i2c.h"

// Hàm lấy nhiệt độ CPU (đơn vị: độ C)
float lay_nhiet_do_cpu() {
    FILE *file_nhiet_do = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
    if (!file_nhiet_do) return 0.0;

    int nhiet_do_milli_celsius;
    fscanf(file_nhiet_do, "%d", &nhiet_do_milli_celsius);
    fclose(file_nhiet_do);

    return nhiet_do_milli_celsius / 1000.0;
}

// Hàm lấy thông tin RAM (đơn vị: MB)
void lay_thong_tin_ram(int *tong_ram_mb, int *ram_dang_dung_mb) {
    FILE *file_meminfo = fopen("/proc/meminfo", "r");
    if (!file_meminfo) return;

    char dong_hien_tai[256];
    int tong_ram_kb      = 0;
    int ram_con_trong_kb = 0;

    while (fgets(dong_hien_tai, sizeof(dong_hien_tai), file_meminfo)) {
        if (sscanf(dong_hien_tai, "MemTotal: %d kB",     &tong_ram_kb)      == 1) continue;
        if (sscanf(dong_hien_tai, "MemAvailable: %d kB", &ram_con_trong_kb) == 1) continue;
    }
    fclose(file_meminfo);

    *tong_ram_mb      = tong_ram_kb / 1024;
    *ram_dang_dung_mb = (tong_ram_kb - ram_con_trong_kb) / 1024;
}

// Hàm lấy địa chỉ IP (hỗ trợ cả WiFi và LAN)
// - Nếu có kết nối: ghi IP vào chuoi_ip_out, trả về 1
// - Nếu chưa kết nối: trả về 0
int lay_ip_mang(char *chuoi_ip_out, size_t kich_thuoc_buffer) {
    struct ifaddrs *danh_sach_interface = NULL;
    struct ifaddrs *interface_hien_tai  = NULL;

    // Lấy danh sách tất cả các network interface trên hệ thống
    if (getifaddrs(&danh_sach_interface) == -1) {
        strncpy(chuoi_ip_out, "Loi doc IP", kich_thuoc_buffer);
        return 0;
    }

    int da_tim_thay_mang = 0;

    for (interface_hien_tai = danh_sach_interface;
         interface_hien_tai != NULL;
         interface_hien_tai = interface_hien_tai->ifa_next)
    {
        // Bỏ qua nếu interface không có địa chỉ
        if (!interface_hien_tai->ifa_addr) continue;

        // Chỉ lấy địa chỉ IPv4
        int la_ipv4 = (interface_hien_tai->ifa_addr->sa_family == AF_INET);

        // Lấy IP của WiFi (wlan0) hoặc cáp mạng LAN (eth0)
        int la_wifi_hoac_lan = (strcmp(interface_hien_tai->ifa_name, "wlan0") == 0 || 
                                strcmp(interface_hien_tai->ifa_name, "eth0") == 0);

        if (la_ipv4 && la_wifi_hoac_lan) {
            struct sockaddr_in *dia_chi_ipv4 =
                (struct sockaddr_in *)interface_hien_tai->ifa_addr;

            // Chuyển IP từ dạng nhị phân sang chuỗi (vd: "192.168.1.10")
            inet_ntop(AF_INET,
                      &dia_chi_ipv4->sin_addr,
                      chuoi_ip_out,
                      kich_thuoc_buffer);

            da_tim_thay_mang = 1;
            break;
        }
    }

    // Giải phóng bộ nhớ
    freeifaddrs(danh_sach_interface);
    return da_tim_thay_mang;
}

int main() {
    // Khởi tạo màn hình OLED tại bus I2C 1, địa chỉ 0x3C
    char *duong_dan_i2c = "/dev/i2c-1";
    if (ssd1306_begin(SSD1306_SWITCHCAPVCC, SSD1306_I2C_ADDRESS, duong_dan_i2c) == 0) {
        printf("Loi: Khong the ket noi voi man hinh OLED!\n");
        return 1;
    }

    char chuoi_nhiet_do[32];
    char chuoi_ram_chi_tiet[32];
    char chuoi_hien_thi_ip[32];  // Dòng hiển thị IP hoặc "Chua ket noi"
    char dia_chi_ip[INET_ADDRSTRLEN]; // Chứa IP dạng "xxx.xxx.xxx.xxx"

    while (1) {
        printf(">>> Dang cap nhat du lieu...\n");
        // 1. Thu thập dữ liệu
        float nhiet_do_cpu     = lay_nhiet_do_cpu();
        int   tong_ram_mb      = 0;
        int   ram_dang_dung_mb = 0;
        lay_thong_tin_ram(&tong_ram_mb, &ram_dang_dung_mb);

        // 2. Kiểm tra mạng và lấy IP
        int co_ket_noi_mang = lay_ip_mang(dia_chi_ip, sizeof(dia_chi_ip));
        if (co_ket_noi_mang) {
            sprintf(chuoi_hien_thi_ip, "IP:%s", dia_chi_ip);
        } else {
            sprintf(chuoi_hien_thi_ip, "Chua ket noi Mang");
        }

        // 3. Định dạng chuỗi hiển thị
        sprintf(chuoi_nhiet_do,     "CPU: %.1f C",       nhiet_do_cpu);
        sprintf(chuoi_ram_chi_tiet, "RAM: %d/%dMB",      ram_dang_dung_mb, tong_ram_mb);
        printf(">>> %s | %s | %s\n", chuoi_hien_thi_ip, chuoi_nhiet_do, chuoi_ram_chi_tiet);
        // 4. Hiển thị lên màn hình OLED (128x64 px, font 5x8)
        ssd1306_clearDisplay();
        //         x   y   nội dung
        ssd1306_drawString(0, 16, chuoi_hien_thi_ip);   // Dòng 2: IP Mạng
        ssd1306_drawString(0, 32, chuoi_nhiet_do);      // Dòng 3: Nhiệt độ
        ssd1306_drawString(0, 48, chuoi_ram_chi_tiet);  // Dòng 4: RAM
        ssd1306_display();

        // Cập nhật mỗi 2 giây
        sleep(2);
    }
    return 0;
}