import socket
import json
import threading
import time

class TrafficNetwork:
    def __init__(self, is_station_a=True, target_ip="192.168.1.100", port=5005):
        self.is_station_a = is_station_a
        self.target_ip = target_ip
        self.port = port
        self.remote_data = {"ket": False, "xe": 0}
        self.running = True
        
        # Tạo socket
        self.sock = socket.socket(socket.AF_socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None

        # Chạy luồng nhận dữ liệu ngầm
        threading.Thread(target=self._network_loop, daemon=True).start()

    def _network_loop(self):
        if self.is_station_a:
            # Trạm A làm Server
            self.sock.bind(('0.0.0.0', self.port))
            self.sock.listen(1)
            print(f"Station A: Waiting for Station B at {self.port}...")
            self.conn, addr = self.sock.accept()
            print(f"Station A: Connected by {addr}")
        else:
            # Trạm B làm Client
            while self.running:
                try:
                    self.sock.connect((self.target_ip, self.port))
                    self.conn = self.sock
                    print(f"Station B: Connected to Station A at {self.target_ip}")
                    break
                except:
                     time.sleep(2) # Thử lại sau 2 giây nếu chưa thấy Trạm A

        # Vòng lặp nhận dữ liệu
        while self.running and self.conn:
            try:
                data = self.conn.recv(1024).decode('utf-8')
                if data:
                    self.remote_data = json.loads(data)
            except:
                break

    def send_status(self, is_jam, vehicle_count):
        """Gửi trạng thái của trạm hiện tại cho trạm đối diện"""
        if self.conn:
            try:
                msg = json.dumps({"ket": is_jam, "xe": vehicle_count})
                self.conn.sendall(msg.encode('utf-8'))
            except:
                print("Network: Send failed")

    def get_remote_data(self):
        return self.remote_data