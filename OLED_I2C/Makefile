# ============================================================
#  Makefile — Pi Status OLED
#  Chạy lệnh: make
#  Dọn dẹp  : make clean
# ============================================================

CC      = gcc
TARGET  = pi_status
SRCS    = main.c ssd1306_i2c.c
OBJS    = $(SRCS:.c=.o)

# -lm : thư viện toán học (dùng cho phép tính float)
LIBS    = -lm

# Cờ cảnh báo + tối ưu nhẹ
CFLAGS  = -Wall -Wextra -O1

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)
	@echo ">>> Build thanh cong! Chay bang: sudo ./$(TARGET)"

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) $(TARGET)
	@echo ">>> Da xoa file build."