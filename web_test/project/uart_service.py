import threading
import time
try:
    import serial
except ImportError:
    serial = None

class UARTService:
    def __init__(self, port="/dev/ttyAMA0", baudrate=115200):
        self.ser = None
        if serial:
            try:
                self.ser = serial.Serial(port, baudrate, timeout=1)
                print(f"[UART] Đã mở cổng {port}")
            except:
                print("[UART] Không tìm thấy cổng Serial (Bỏ qua nếu chạy Win)")
        
    def send(self, msg):
        if self.ser and self.ser.is_open:
            self.ser.write((msg + "\n").encode())

    def start_listening(self, trigger_callback):
        if not self.ser: return
        def run():
            while True:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode().strip()
                    if line.lower() == "yell":
                        trigger_callback()
                time.sleep(0.1)
        threading.Thread(target=run, daemon=True).start()