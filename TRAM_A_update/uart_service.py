import threading
import time
import queue

# --- THỬ IMPORT THƯ VIỆN SERIAL ---
try:
    import serial
except ImportError:
    serial = None

class UART_config:
    def __init__(self, port="/dev/ttyAMA0", baudrate=115200):
        self.ser = None
        self.send_queue = queue.Queue(maxsize=50)

    def send(self, msg):
        try:
            self.send_queue.put(msg, timeout=0.1)
        except queue.Full:
            print("[UART] Queue full, lệnh bị drop:", msg) # Hàng đợi để gửi lệnh mượt mà
        
        if serial:
            try:
                # Cấu hình cổng Serial
                self.ser = serial.Serial(port, baudrate, timeout=1)
                print(f"[UART] Đã mở cổng {port} thành công.")
                
                # Chạy luồng gửi dữ liệu riêng để không làm treo Logic chính
                threading.Thread(target=self._send_worker, daemon=True).start()
            except Exception as e:
                print(f"[UART] Lỗi/Không tìm thấy cổng Serial: {e}")
        
    def _send_worker(self):
        """Luồng chạy ngầm xử lý việc gửi dữ liệu từ hàng đợi"""
        while True:
            msg = self.send_queue.get()
            if self.ser and self.ser.is_open:
                try:
                    # Gửi đúng biến (m1, m2, m3...) kèm ký tự xuống dòng
                    data_to_send = (str(msg) + "\n").encode('utf-8')
                    self.ser.write(data_to_send)
                    
                    # --- THÊM DÒNG NÀY ĐỂ DEBUG ---
                    print(f"[UART] >>> ĐANG GỬI XUỐNG ESP32: {msg}") 
                    # ------------------------------
                    
                except Exception as e:
                    print(f"[UART] Lỗi gửi: {e}")
            else:
                # Debug trường hợp cổng Serial chưa mở mà Logic đã đòi gửi
                print(f"[UART] CẢNH BÁO: Cổng Serial chưa mở, không thể gửi: {msg}")

            self.send_queue.task_done()
            time.sleep(0.01)

    def send(self, msg):
        """
        Nhận biến từ TrafficLogic (vd: "m1", "m2"...) 
        và đưa vào hàng đợi để gửi đi
        """
        if msg:
            self.send_queue.put(msg)

    def start_listening(self, nhanbien):
        if not self.ser: 
            return

        def run():
            """Vòng lặp lắng nghe lệnh 'run' từ MCU"""
            while True:
                try:
                    if self.ser.in_waiting:
                        # Đọc, giải mã và làm sạch dữ liệu nhận được
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        if line.lower() == "run":
                            print("[UART] <<< Nhận 'run' -> Kích hoạt AI")
                            nhanbien() 
                except Exception as e:
                    print(f"[UART] Lỗi nhận: {e}")
                
                time.sleep(0.05) 

        threading.Thread(target=run, daemon=True).start()