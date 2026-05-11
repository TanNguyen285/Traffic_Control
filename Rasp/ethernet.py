import socket
import json
import threading
import time

class EthernetService:
    def __init__(self, station_id, peer_hostname, port):
        self.station_id = station_id.upper()
        self.peer_hostname = peer_hostname 
        self.port = port
        self.remote_data = {'ket': False, 'xe': 0}
        self.conn = None
        self.running = True
        # Biến quan trọng: Chỉ khi True mới bắt đầu tìm kiếm/đợi kết nối
        self.active = False 
        
        threading.Thread(target=self.ketnoiethernet, daemon=True).start()

    def ketnoiethernet(self):
        while self.running:
            # Nếu đang ở chế độ SINGLE (active=False), chỉ đứng đợi, không làm gì cả
            if not self.active:
                time.sleep(1)
                continue

            try:
                if self.station_id == 'TRAM_A': 
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.settimeout(5) # Trạm A đợi 5s không có ai kết nối thì vòng lại
                        s.bind(('0.0.0.0', self.port))
                        s.listen(1)
                        print(f"[ETH] Trạm A đang ĐỢI kết nối tại cổng {self.port}...")
                        try:
                            self.conn, addr = s.accept()
                            print(f"[ETH] Đã kết nối với: {addr}")
                            self._receive_loop()
                        except socket.timeout:
                            continue 
                else:
                    # Trạm B (Client)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(3) # Trạm B chỉ thử tìm A trong 3 giây
                        try:
                            real_ip = socket.gethostbyname(self.peer_hostname)
                            s.connect((real_ip, self.port))
                            self.conn = s
                            print(f"[ETH] Đã kết nối tới {self.peer_hostname}")
                            self._receive_loop()
                        except (socket.gaierror, socket.timeout, ConnectionRefusedError):
                            # Nếu không thấy A, in log rồi ngủ 5s, KHÔNG dùng 'continue' ngay lập tức
                            print(f"[ETH] Chưa thấy {self.peer_hostname}, chạy ĐỘC LẬP...")
                            time.sleep(5) 
            except Exception as e:
                print(f"[ETH] Lỗi: {e}")
                time.sleep(2)

    def _receive_loop(self):
        buffer = ""
        while self.running and self.conn:
            try:
                self.conn.settimeout(5) # Tránh treo nếu mất kết nối đột ngột
                chunk = self.conn.recv(1024).decode('utf-8')
                if not chunk: break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.remote_data = json.loads(line)
            except:
                break
        self.conn = None

    def send_data(self, is_jam, xe_count, ready=False):
        if self.conn:
            try:
                payload = json.dumps({'ket': is_jam, 'xe': xe_count, 'ready': ready}) + "\n"
                self.conn.sendall(payload.encode('utf-8'))
            except:
                self.conn = None

    def get_remote_status(self):
        if not self.conn:
            return {'ket': False, 'xe': 0, 'ready': False, 'connected': False}
        data = self.remote_data.copy()
        data['connected'] = True
        if 'ready' not in data:
            data['ready'] = False
        return data
