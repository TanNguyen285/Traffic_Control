import threading
import time

# --- THỬ IMPORT THƯ VIỆN SERIAL ---
# Thư viện pyserial dùng để giao tiếp qua cổng COM/UART
try:
    import serial
except ImportError:
    serial = None

class UART_config:
    def __init__(self, port="/dev/ttyAMA0", baudrate=115200):
        self.ser = None
        if serial:
            try:
                # Cấu hình cổng Serial với thời gian chờ (timeout) là 1 giây
                self.ser = serial.Serial(port, baudrate, timeout=1)
                print(f"[UART] Đã mở cổng {port} thành công.")
            except Exception as e:
                # Nếu lỗi (do sai cổng hoặc đang chạy trên Windows không có cổng này)
                print(f"[UART] Lỗi/Không tìm thấy cổng Serial: {e}")
        
    def send(self, msg):
        if self.ser and self.ser.is_open:
            # Gửi tin nhắn kèm ký tự xuống dòng (\n) và mã hóa sang dạng byte
            self.ser.write((msg + "\n").encode())
            # print(f"[UART] Đã gửi: {msg}") # Debug nếu cần

    def start_listening(self, trigger_callback):
        if not self.ser: 
            return

        def run():
            """Vòng lặp chạy ngầm để liên tục kiểm tra dữ liệu đến"""
            while True:
                try:
                    # Kiểm tra xem có dữ liệu nào đang chờ trong hàng đợi không
                    if self.ser.in_waiting:
                        # Đọc một dòng dữ liệu, giải mã (decode) và xóa khoảng trắng thừa (strip)
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        # LOGIC KIỂM TRA LỆNH:
                        # Nếu nhận được lệnh "yell" (không phân biệt hoa thường)
                        if line.lower() == "yell":
                            print("[UART] Nhận lệnh 'yell' -> Kích hoạt Callback xử lý AI")
                            trigger_callback() # Gọi hàm xử lý (vd: chụp ảnh, chạy YOLO)
                except Exception as e:
                    print(f"[UART] Lỗi trong quá trình nghe: {e}")
                
                # Nghỉ 100ms để giảm tải cho CPU (không chiếm dụng 100% nhân CPU)
                time.sleep(0.1)

        # Chạy hàm run() trong một luồng riêng biệt (Thread) để không làm treo giao diện Web
        daemon=True #giúp thread tự tắt khi chương trình chính (Flask) dừng
        threading.Thread(target=run, daemon=True).start()