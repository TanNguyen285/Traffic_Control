#ifndef SSD1306_I2C_H
#define SSD1306_I2C_H

#include <stdint.h>

// ============================================================
//  Kích thước màn hình
// ============================================================
#define SSD1306_WIDTH   128
#define SSD1306_HEIGHT   64

// ============================================================
//  Địa chỉ I2C mặc định
// ============================================================
#define SSD1306_I2C_ADDRESS  0x3C

// ============================================================
//  Chế độ nguồn (dùng khi gọi ssd1306_begin)
// ============================================================
#define SSD1306_SWITCHCAPVCC  0x02   // Dùng bộ tăng áp nội bộ (phổ biến)
#define SSD1306_EXTERNALVCC   0x01   // Dùng nguồn ngoài

// ============================================================
//  Màu pixel (SSD1306 chỉ có 2 màu: sáng / tắt)
// ============================================================
#define SSD1306_WHITE  1
#define SSD1306_BLACK  0

// ============================================================
//  API công khai
// ============================================================

/**
 * Khởi tạo màn hình OLED.
 * @param vcc_state   SSD1306_SWITCHCAPVCC hoặc SSD1306_EXTERNALVCC
 * @param i2c_address Địa chỉ I2C (thường là 0x3C)
 * @param i2c_device  Đường dẫn thiết bị I2C, ví dụ "/dev/i2c-1"
 * @return 1 nếu thành công, 0 nếu lỗi
 */
int ssd1306_begin(uint8_t vcc_state, uint8_t i2c_address, const char *i2c_device);

/** Xoá toàn bộ bộ đệm về màu đen */
void ssd1306_clearDisplay(void);

/** Đẩy bộ đệm lên màn hình (gọi sau khi vẽ xong) */
void ssd1306_display(void);

/**
 * Vẽ một pixel tại (x, y).
 * @param mau  SSD1306_WHITE (sáng) hoặc SSD1306_BLACK (tắt)
 */
void ssd1306_drawPixel(int x, int y, int mau);

/**
 * Hiển thị chuỗi ký tự tại vị trí (x, y).
 * Font mặc định: 5x8 pixel mỗi ký tự, cách nhau 1 pixel.
 */
void ssd1306_drawString(int x, int y, const char *chuoi);

/**
 * Vẽ một ký tự đơn tại (x, y).
 */
void ssd1306_drawChar(int x, int y, char ky_tu);

#endif /* SSD1306_I2C_H */