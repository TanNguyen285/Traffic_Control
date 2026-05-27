import socket
import json
import threading
import time


class EthernetService:
    def __init__(self, station_id: str, peer_hostname: str, port: int):
        self.station_id    = station_id.upper()
        self.peer_hostname = peer_hostname
        self.port          = port

        self._lock       = threading.Lock()
        self._connected  = False
        self._conn       = None
        self._started    = False

        self._remote = {'CNN': False, 'xe': 0, 'ready': False, 'fresh': False, 'stage': ''}
        self._data_event = threading.Event()

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._connected

    def start(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._connect_loop, daemon=True).start()
        print(f"[ETH] Khởi động ({self.station_id})")

    def send(self, ket: bool, xe: int, ready: bool = False, stage: str = "") -> bool:
        with self._lock:
            conn = self._conn
        if not conn:
            return False
        try:
            payload = json.dumps({'CNN': ket, 'xe': xe, 'ready': ready,
                                  'fresh': True, 'stage': stage}) + "\n"
            conn.sendall(payload.encode('utf-8'))
            return True
        except Exception:
            self._mark_disconnected()
            return False

    def get_remote(self) -> dict:
        with self._lock:
            return dict(self._remote)

    def wait_fresh(self, timeout: float = 10.0, expected_stage: str = "") -> dict | None:
        deadline = time.time() + timeout
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            self._data_event.wait(timeout=min(remaining, 0.5))
            self._data_event.clear()
            with self._lock:
                if (self._remote['fresh'] and self._remote['ready']
                        and self._remote.get('stage') == expected_stage):
                    self._remote['fresh'] = False
                    self._remote['ready'] = False
                    return dict(self._remote)
            if not self.connected:
                return None

    def clear(self):
        with self._lock:
            self._remote['CNN']   = False
            self._remote['xe']    = 0
            self._remote['ready'] = False
            self._remote['fresh'] = False
            self._remote['stage'] = ''

    def _connect_loop(self):
        while True:
            if self.station_id == 'TRAM_A':
                self._run_server()
            else:
                self._run_client()
            time.sleep(3)

    def _run_server(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(('0.0.0.0', self.port))
            srv.listen(1)
            srv.settimeout(10)
            print(f"[ETH] Server chờ kết nối tại cổng {self.port}...")
            while True:
                try:
                    conn, addr = srv.accept()
                    print(f"[ETH] Client kết nối: {addr}")
                    self._setup_conn(conn)
                    self._receive_loop()
                    print(f"[ETH] Mất kết nối, chờ client mới...")
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[ETH] Server lỗi: {e}")
                    time.sleep(1)
        except Exception as e:
            print(f"[ETH] Bind lỗi: {e}")

    def _run_client(self):
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                ip = socket.gethostbyname(self.peer_hostname)
                s.connect((ip, self.port))
                print(f"[ETH] Đã kết nối tới {self.peer_hostname}")
                self._setup_conn(s)
                self._receive_loop()
                print(f"[ETH] Mất kết nối, thử lại...")
            except (socket.gaierror, socket.timeout, ConnectionRefusedError):
                print(f"[ETH] Chưa thấy {self.peer_hostname}, thử lại sau 5s...")
                time.sleep(5)
            except Exception as e:
                print(f"[ETH] Client lỗi: {e}")
                time.sleep(3)

    def _setup_conn(self, conn):
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY,  1)
        conn.setsockopt(socket.SOL_SOCKET,  socket.SO_KEEPALIVE, 1)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,  10)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT,   3)
        conn.settimeout(None)
        with self._lock:
            self._conn      = conn
            self._connected = True

    def _receive_loop(self):
        buffer = ""
        while True:
            with self._lock:
                conn = self._conn
            if not conn:
                break
            try:
                chunk = conn.recv(1024).decode('utf-8')
                if not chunk:
                    break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        if parsed.get('fresh', False):
                            with self._lock:
                                self._remote['CNN']   = parsed.get('CNN',   False)
                                self._remote['xe']    = parsed.get('xe',    0)
                                self._remote['ready'] = parsed.get('ready', False)
                                self._remote['stage'] = parsed.get('stage', '')
                                self._remote['fresh'] = True
                            self._data_event.set()
                    except json.JSONDecodeError:
                        pass
            except Exception:
                break
        self._mark_disconnected()

    def _mark_disconnected(self):
        with self._lock:
            self._connected      = False
            self._conn           = None
            self._remote['fresh'] = False
        self._data_event.set()