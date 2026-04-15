import socket
import json
import threading
import time

class EthernetService:
    def __init__(self, station_id, peer_ip, port=8000):
        self.station_id = station_id.upper()
        self.peer_ip = peer_ip
        self.port = port
        self.remote_data = {'ket': False, 'xe': 0}
        self.conn = None
        self.running = True
        
        # Chạy luồng kết nối ngầm
        threading.Thread(target=self.ketnoiethernet, daemon=True).start()

    def ketnoiethernet(self):
        while self.running:
            try:
                if self.station_id == 'A':
                    # Trạm A làm Server
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.bind(('0.0.0.0', self.port))
                        s.listen(1)
                        self.conn, addr = s.accept()
                        self._receive_loop()
                else:
                    # Trạm B làm Client
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((self.peer_ip, self.port))
                        self.conn = s
                        self._receive_loop()
            except Exception as e:
                self.conn = None
                time.sleep(2) # Đợi 2s rồi thử kết nối lại

    def _receive_loop(self):
            buffer = ""
            while self.running and self.conn:
                try:
                    chunk = self.conn.recv(1024).decode('utf-8')
                    if not chunk: break
                    buffer += chunk
                    
                    # Tìm ký tự xuống dòng để tách gói tin JSON
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line.strip():
                            self.remote_data = json.loads(line)
                except:
                    break
            self.conn = None

    def send_data(self, is_jam, xe_count):
        if self.conn:
            try:
                # Thêm \n ở cuối gói tin
                payload = json.dumps({'ket': is_jam, 'xe': xe_count}) + "\n"
                self.conn.sendall(payload.encode('utf-8'))
            except:
                self.conn = None

    def get_remote_status(self):
        """Lấy dữ liệu mới nhất nhận được từ máy đối diện"""
        return self.remote_data