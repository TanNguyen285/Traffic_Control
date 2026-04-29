import threading
import time
import queue

try:
    import serial
except ImportError:
    serial = None

class UART_config:
    def __init__(self, port="/dev/ttyAMA0", baudrate=115200):
        self.ser = None
        self.port = port
        self.baudrate = baudrate
        self.send_queue = queue.Queue(maxsize=50)
        
        if serial:
            try:
                # MỞ CỔNG NGAY KHI KHỞI TẠO
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                print(f"[UART] Đã mở cổng {self.port} thành công.")
                
                # Chạy luồng gửi dữ liệu
                threading.Thread(target=self._send_worker, daemon=True).start()
            except Exception as e:
                print(f"[UART] Lỗi không mở được cổng: {e}")
        else:
            print("[UART] Thiếu thư viện pyserial!")

    def _send_worker(self):
        """Luồng gửi dữ liệu xuống ESP32"""
        while True:
            msg = self.send_queue.get()
            if self.ser and self.ser.is_open:
                try:
                    # Gửi kèm \n để ESP32 nhận biết kết thúc lệnh
                    data_to_send = (str(msg) + "\n").encode('utf-8')
                    self.ser.write(data_to_send)
                    print(f"[UART] >>> ĐANG GỬI XUỐNG ESP32: {msg}") 
                except Exception as e:
                    print(f"[UART] Lỗi gửi: {e}")
            self.send_queue.task_done()
            time.sleep(0.01)

    def send(self, msg):
        """Đưa tin nhắn vào hàng đợi để gửi"""
        if msg and not self.send_queue.full():
            self.send_queue.put(msg)
        else:
            print(f"[UART] Bỏ qua lệnh '{msg}' do hàng đợi đầy hoặc msg rỗng")

    def start_listening(self, callback_func):
        """Lắng nghe 'run' hoặc 'run1' từ ESP32"""
        if not self.ser:
            print("[UART] Không thể nghe vì chưa mở được cổng Serial!")
            return

        def run_loop():
            print(f"[UART] Bắt đầu lắng nghe trên {self.port}...")
            while True:
                try:
                    if self.ser.in_waiting:
                        # Đọc một dòng từ ESP32
                        raw_data = self.ser.readline()
                        line = raw_data.decode('utf-8', errors='ignore').strip().lower()
                        
                        if line:
                            print(f"[UART] <<< Nhận dữ liệu thô: {line}")
                            if line == "run":
                                print("[UART] Kích hoạt AI Scan")
                                callback_func("run")
                            elif line == "run1":
                                print("[UART] Kích hoạt Xả trạm")
                                callback_func("run1")
                except Exception as e:
                    print(f"[UART] Lỗi nhận dữ liệu: {e}")
                time.sleep(0.05)

        threading.Thread(target=run_loop, daemon=True).start()