#include "ssd1306_i2c.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>

// ============================================================
//  Lệnh điều khiển SSD1306
// ============================================================
#define CMD_DISPLAY_OFF          0xAE
#define CMD_DISPLAY_ON           0xAF
#define CMD_SET_DISPLAY_CLOCK    0xD5
#define CMD_SET_MULTIPLEX        0xA8
#define CMD_SET_DISPLAY_OFFSET   0xD3
#define CMD_SET_START_LINE       0x40
#define CMD_CHARGE_PUMP          0x8D
#define CMD_MEMORY_MODE          0x20
#define CMD_SET_SEGMENT_REMAP    0xA1
#define CMD_COM_SCAN_DEC         0xC8
#define CMD_SET_COM_PINS         0xDA
#define CMD_SET_CONTRAST         0x81
#define CMD_SET_PRECHARGE        0xD9
#define CMD_SET_VCOM_DETECT      0xDB
#define CMD_DISPLAY_ALL_ON_RESUME 0xA4
#define CMD_NORMAL_DISPLAY       0xA6
#define CMD_COLUMN_ADDR          0x21
#define CMD_PAGE_ADDR            0x22

// ============================================================
//  Bộ đệm màn hình: 128 x 64 / 8 = 1024 byte
// ============================================================
#define BUF_SIZE  (SSD1306_WIDTH * SSD1306_HEIGHT / 8)
static uint8_t bo_dem_man_hinh[BUF_SIZE];

// ============================================================
//  Biến toàn cục nội bộ
// ============================================================
static int     fd_i2c      = -1;   // File descriptor I2C
static uint8_t dia_chi_i2c = 0x3C; // Địa chỉ thiết bị

// ============================================================
//  Font chữ 5x8 (ASCII 32–126)
//  Mỗi ký tự = 5 byte, mỗi byte = 1 cột 8 pixel
// ============================================================
static const uint8_t font5x8[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, // 32 space
    {0x00,0x00,0x5F,0x00,0x00}, // 33 !
    {0x00,0x07,0x00,0x07,0x00}, // 34 "
    {0x14,0x7F,0x14,0x7F,0x14}, // 35 #
    {0x24,0x2A,0x7F,0x2A,0x12}, // 36 $
    {0x23,0x13,0x08,0x64,0x62}, // 37 %
    {0x36,0x49,0x55,0x22,0x50}, // 38 &
    {0x00,0x05,0x03,0x00,0x00}, // 39 '
    {0x00,0x1C,0x22,0x41,0x00}, // 40 (
    {0x00,0x41,0x22,0x1C,0x00}, // 41 )
    {0x08,0x2A,0x1C,0x2A,0x08}, // 42 *
    {0x08,0x08,0x3E,0x08,0x08}, // 43 +
    {0x00,0x50,0x30,0x00,0x00}, // 44 ,
    {0x08,0x08,0x08,0x08,0x08}, // 45 -
    {0x00,0x60,0x60,0x00,0x00}, // 46 .
    {0x20,0x10,0x08,0x04,0x02}, // 47 /
    {0x3E,0x51,0x49,0x45,0x3E}, // 48 0
    {0x00,0x42,0x7F,0x40,0x00}, // 49 1
    {0x42,0x61,0x51,0x49,0x46}, // 50 2
    {0x21,0x41,0x45,0x4B,0x31}, // 51 3
    {0x18,0x14,0x12,0x7F,0x10}, // 52 4
    {0x27,0x45,0x45,0x45,0x39}, // 53 5
    {0x3C,0x4A,0x49,0x49,0x30}, // 54 6
    {0x01,0x71,0x09,0x05,0x03}, // 55 7
    {0x36,0x49,0x49,0x49,0x36}, // 56 8
    {0x06,0x49,0x49,0x29,0x1E}, // 57 9
    {0x00,0x36,0x36,0x00,0x00}, // 58 :
    {0x00,0x56,0x36,0x00,0x00}, // 59 ;
    {0x08,0x14,0x22,0x41,0x00}, // 60 <
    {0x14,0x14,0x14,0x14,0x14}, // 61 =
    {0x00,0x41,0x22,0x14,0x08}, // 62 >
    {0x02,0x01,0x51,0x09,0x06}, // 63 ?
    {0x32,0x49,0x79,0x41,0x3E}, // 64 @
    {0x7E,0x11,0x11,0x11,0x7E}, // 65 A
    {0x7F,0x49,0x49,0x49,0x36}, // 66 B
    {0x3E,0x41,0x41,0x41,0x22}, // 67 C
    {0x7F,0x41,0x41,0x22,0x1C}, // 68 D
    {0x7F,0x49,0x49,0x49,0x41}, // 69 E
    {0x7F,0x09,0x09,0x09,0x01}, // 70 F
    {0x3E,0x41,0x49,0x49,0x7A}, // 71 G
    {0x7F,0x08,0x08,0x08,0x7F}, // 72 H
    {0x00,0x41,0x7F,0x41,0x00}, // 73 I
    {0x20,0x40,0x41,0x3F,0x01}, // 74 J
    {0x7F,0x08,0x14,0x22,0x41}, // 75 K
    {0x7F,0x40,0x40,0x40,0x40}, // 76 L
    {0x7F,0x02,0x0C,0x02,0x7F}, // 77 M
    {0x7F,0x04,0x08,0x10,0x7F}, // 78 N
    {0x3E,0x41,0x41,0x41,0x3E}, // 79 O
    {0x7F,0x09,0x09,0x09,0x06}, // 80 P
    {0x3E,0x41,0x51,0x21,0x5E}, // 81 Q
    {0x7F,0x09,0x19,0x29,0x46}, // 82 R
    {0x46,0x49,0x49,0x49,0x31}, // 83 S
    {0x01,0x01,0x7F,0x01,0x01}, // 84 T
    {0x3F,0x40,0x40,0x40,0x3F}, // 85 U
    {0x1F,0x20,0x40,0x20,0x1F}, // 86 V
    {0x3F,0x40,0x38,0x40,0x3F}, // 87 W
    {0x63,0x14,0x08,0x14,0x63}, // 88 X
    {0x07,0x08,0x70,0x08,0x07}, // 89 Y
    {0x61,0x51,0x49,0x45,0x43}, // 90 Z
    {0x00,0x7F,0x41,0x41,0x00}, // 91 [
    {0x02,0x04,0x08,0x10,0x20}, // 92 backslash
    {0x00,0x41,0x41,0x7F,0x00}, // 93 ]
    {0x04,0x02,0x01,0x02,0x04}, // 94 ^
    {0x40,0x40,0x40,0x40,0x40}, // 95 _
    {0x00,0x01,0x02,0x04,0x00}, // 96 `
    {0x20,0x54,0x54,0x54,0x78}, // 97  a
    {0x7F,0x48,0x44,0x44,0x38}, // 98  b
    {0x38,0x44,0x44,0x44,0x20}, // 99  c
    {0x38,0x44,0x44,0x48,0x7F}, // 100 d
    {0x38,0x54,0x54,0x54,0x18}, // 101 e
    {0x08,0x7E,0x09,0x01,0x02}, // 102 f
    {0x0C,0x52,0x52,0x52,0x3E}, // 103 g
    {0x7F,0x08,0x04,0x04,0x78}, // 104 h
    {0x00,0x44,0x7D,0x40,0x00}, // 105 i
    {0x20,0x40,0x44,0x3D,0x00}, // 106 j
    {0x7F,0x10,0x28,0x44,0x00}, // 107 k
    {0x00,0x41,0x7F,0x40,0x00}, // 108 l
    {0x7C,0x04,0x18,0x04,0x78}, // 109 m
    {0x7C,0x08,0x04,0x04,0x78}, // 110 n
    {0x38,0x44,0x44,0x44,0x38}, // 111 o
    {0x7C,0x14,0x14,0x14,0x08}, // 112 p
    {0x08,0x14,0x14,0x18,0x7C}, // 113 q
    {0x7C,0x08,0x04,0x04,0x08}, // 114 r
    {0x48,0x54,0x54,0x54,0x20}, // 115 s
    {0x04,0x3F,0x44,0x40,0x20}, // 116 t
    {0x3C,0x40,0x40,0x20,0x7C}, // 117 u
    {0x1C,0x20,0x40,0x20,0x1C}, // 118 v
    {0x3C,0x40,0x30,0x40,0x3C}, // 119 w
    {0x44,0x28,0x10,0x28,0x44}, // 120 x
    {0x0C,0x50,0x50,0x50,0x3C}, // 121 y
    {0x44,0x64,0x54,0x4C,0x44}, // 122 z
    {0x00,0x08,0x36,0x41,0x00}, // 123 {
    {0x00,0x00,0x7F,0x00,0x00}, // 124 |
    {0x00,0x41,0x36,0x08,0x00}, // 125 }
    {0x08,0x08,0x2A,0x1C,0x08}, // 126 ~
};

// ============================================================
//  Hàm nội bộ: gửi 1 byte lệnh xuống SSD1306
// ============================================================
static void gui_lenh(uint8_t lenh) {
    uint8_t goi[2] = { 0x00, lenh }; // 0x00 = Co = Command
    write(fd_i2c, goi, 2);
}

// ============================================================
//  Hàm nội bộ: gửi khối dữ liệu pixel
// ============================================================
static void gui_du_lieu(uint8_t *du_lieu, int do_dai) {
    // Thêm byte điều khiển 0x40 (Co=0, D/C=1 → Data) trước mỗi khối
    uint8_t *goi = malloc(do_dai + 1);
    if (!goi) return;
    goi[0] = 0x40;
    memcpy(goi + 1, du_lieu, do_dai);
    write(fd_i2c, goi, do_dai + 1);
    free(goi);
}

// ============================================================
//  ssd1306_begin
// ============================================================
int ssd1306_begin(uint8_t vcc_state, uint8_t i2c_address, const char *i2c_device) {
    dia_chi_i2c = i2c_address;

    // Mở file I2C
    fd_i2c = open(i2c_device, O_RDWR);
    if (fd_i2c < 0) {
        perror("Khong mo duoc I2C");
        return 0;
    }

    // Chọn địa chỉ slave
    if (ioctl(fd_i2c, I2C_SLAVE, dia_chi_i2c) < 0) {
        perror("Khong dat duoc dia chi I2C");
        close(fd_i2c);
        fd_i2c = -1;
        return 0;
    }

    // Chuỗi lệnh khởi tạo theo datasheet SSD1306
    gui_lenh(CMD_DISPLAY_OFF);

    gui_lenh(CMD_SET_DISPLAY_CLOCK);
    gui_lenh(0x80);                         // Tần số dao động mặc định

    gui_lenh(CMD_SET_MULTIPLEX);
    gui_lenh(SSD1306_HEIGHT - 1);           // 63 cho màn 128x64

    gui_lenh(CMD_SET_DISPLAY_OFFSET);
    gui_lenh(0x00);                         // Không dịch offset

    gui_lenh(CMD_SET_START_LINE | 0x00);    // Start line = 0

    gui_lenh(CMD_CHARGE_PUMP);
    gui_lenh((vcc_state == SSD1306_EXTERNALVCC) ? 0x10 : 0x14);

    gui_lenh(CMD_MEMORY_MODE);
    gui_lenh(0x00);                         // Chế độ Horizontal Addressing

    gui_lenh(CMD_SET_SEGMENT_REMAP);        // Lật ngang (phù hợp hầu hết module)
    gui_lenh(CMD_COM_SCAN_DEC);             // Quét từ dưới lên

    gui_lenh(CMD_SET_COM_PINS);
    gui_lenh(0x12);                         // Cấu hình COM cho 128x64

    gui_lenh(CMD_SET_CONTRAST);
    gui_lenh((vcc_state == SSD1306_EXTERNALVCC) ? 0x9F : 0xCF);

    gui_lenh(CMD_SET_PRECHARGE);
    gui_lenh((vcc_state == SSD1306_EXTERNALVCC) ? 0x22 : 0xF1);

    gui_lenh(CMD_SET_VCOM_DETECT);
    gui_lenh(0x40);

    gui_lenh(CMD_DISPLAY_ALL_ON_RESUME);    // Hiển thị từ RAM
    gui_lenh(CMD_NORMAL_DISPLAY);           // Không đảo màu
    gui_lenh(CMD_DISPLAY_ON);              // Bật màn hình

    // Xoá màn hình khi mới khởi động
    ssd1306_clearDisplay();
    ssd1306_display();

    return 1;
}

// ============================================================
//  ssd1306_clearDisplay
// ============================================================
void ssd1306_clearDisplay(void) {
    memset(bo_dem_man_hinh, 0, BUF_SIZE);
}

// ============================================================
//  ssd1306_display  — đẩy bộ đệm lên màn hình
// ============================================================
void ssd1306_display(void) {
    // Đặt vùng ghi: toàn bộ màn hình
    gui_lenh(CMD_COLUMN_ADDR);
    gui_lenh(0);
    gui_lenh(SSD1306_WIDTH - 1);

    gui_lenh(CMD_PAGE_ADDR);
    gui_lenh(0);
    gui_lenh((SSD1306_HEIGHT / 8) - 1);   // 7 cho màn 128x64

    // Gửi từng khối 16 byte để tránh tràn I2C buffer
    int kich_thuoc_khoi = 16;
    for (int vi_tri = 0; vi_tri < BUF_SIZE; vi_tri += kich_thuoc_khoi) {
        int con_lai = BUF_SIZE - vi_tri;
        int do_dai  = (con_lai < kich_thuoc_khoi) ? con_lai : kich_thuoc_khoi;
        gui_du_lieu(&bo_dem_man_hinh[vi_tri], do_dai);
    }
}

// ============================================================
//  ssd1306_drawPixel
// ============================================================
void ssd1306_drawPixel(int x, int y, int mau) {
    if (x < 0 || x >= SSD1306_WIDTH)  return;
    if (y < 0 || y >= SSD1306_HEIGHT) return;

    // Mỗi byte quản lý 8 pixel theo chiều dọc
    // Byte tại: bo_dem[x + (y/8)*128], bit tại vị trí (y%8)
    if (mau)
        bo_dem_man_hinh[x + (y / 8) * SSD1306_WIDTH] |=  (1 << (y % 8));
    else
        bo_dem_man_hinh[x + (y / 8) * SSD1306_WIDTH] &= ~(1 << (y % 8));
}

// ============================================================
//  ssd1306_drawChar  — vẽ 1 ký tự 5x8
// ============================================================
void ssd1306_drawChar(int x, int y, char ky_tu) {
    if (ky_tu < 32 || ky_tu > 126) ky_tu = '?';

    int chi_so_font = ky_tu - 32; // Font bắt đầu từ ASCII 32 (space)

    for (int cot = 0; cot < 5; cot++) {
        uint8_t duong_cot = font5x8[chi_so_font][cot];
        for (int hang = 0; hang < 8; hang++) {
            // Vẽ từng bit từ thấp đến cao
            int sang = (duong_cot >> hang) & 0x01;
            ssd1306_drawPixel(x + cot, y + hang, sang);
        }
    }
}

// ============================================================
//  ssd1306_drawString  — vẽ chuỗi ký tự
// ============================================================
void ssd1306_drawString(int x, int y, const char *chuoi) {
    int vi_tri_x = x;

    while (*chuoi) {
        // Xuống dòng tự động nếu chạm cạnh phải
        if (vi_tri_x + 6 > SSD1306_WIDTH) {
            vi_tri_x  = x;
            y        += 8;
        }
        if (y + 8 > SSD1306_HEIGHT) break; // Hết màn hình, dừng lại

        ssd1306_drawChar(vi_tri_x, y, *chuoi);
        vi_tri_x += 6; // 5 pixel chữ + 1 pixel khoảng cách
        chuoi++;
    }
}