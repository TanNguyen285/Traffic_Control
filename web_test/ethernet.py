import socket
import json
import threading
import time

class EthernetService:
    def __init__(self, station_id, peer_hostname, port=8000):
        self.station_id = station_id.upper()
        # Đổi tên biến từ peer_ip thành peer_hostname cho đúng bản chất
        self.peer_hostname = peer_hostname 
        self.port = port
        self.remote_data = {'ket': False, 'xe': 0}
        self.conn = None
        self.running = True
        
        threading.Thread(target=self.ketnoiethernet, daemon=True).start()

    def ketnoiethernet(self):
        while self.running:
            try:
                if self.station_id == 'Tram_A':
                    # Trạm A làm Server: Giữ nguyên 0.0.0.0 để nhận mọi kết nối
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.bind(('0.0.0.0', self.port))
                        s.listen(1)
                        print(f"Trạm A đang chờ kết nối tại cổng {self.port}...")
                        self.conn, addr = s.accept()
                        print(f"Đã kết nối với: {addr}")
                        self._receive_loop()
                else:
                    # Trạm B làm Client: Dịch hostname thành IP trước khi gọi connect
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        try:
                            # Tự động dịch 'trama.local' thành IP thực tế
                            real_ip = socket.gethostbyname(self.peer_hostname)
                            print(f"Đang kết nối tới {self.peer_hostname} ({real_ip})...")
                            s.connect((real_ip, self.port))
                            self.conn = s
                            self._receive_loop()
                        except socket.gaierror:
                            print(f"Lỗi: Không tìm thấy máy {self.peer_hostname}. Đang thử lại...")
                            time.sleep(2)
                            continue
            except Exception as e:
                print(f"Lỗi kết nối: {e}")
                self.conn = None
                time.sleep(2)

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