import socket
import json
import threading
import time

class EthernetService:
    def __init__(self, station_id, peer_ip, port=5005):
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
        while self.running and self.conn:
            try:
                data = self.conn.recv(1024).decode('utf-8')
                if not data: break
                self.remote_data = json.loads(data)
            except:
                break
        self.conn = None

    def send_data(self, is_jam, xe_count):
        """Gửi trạng thái hiện tại sang máy đối diện"""
        if self.conn:
            try:
                payload = json.dumps({'ket': is_jam, 'xe': xe_count})
                self.conn.sendall(payload.encode('utf-8'))
            except:
                self.conn = None

    def get_remote_status(self):
        """Lấy dữ liệu mới nhất nhận được từ máy đối diện"""
        return self.remote_data