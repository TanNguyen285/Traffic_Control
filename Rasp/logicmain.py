import os
import time
import cv2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, eth_service, station_id='TRAM_A'):
        self.ai       = yolo_ai
        self.cnn      = cnn_service
        self.pre_proc = pre_proc
        self.uart     = uart
        self.cam      = cam
        self.eth      = eth_service
        self.id       = station_id.upper()

        self.bien_run        = False
        self.operation_mode  = "single"

        self.frame_raw    = None
        self.frame_cnn    = None
        self.frame_yolo   = None
        self.brightness   = 0
        self.ket_local    = False
        self.xe_local     = 0
        self.yolo_results = {"counts": [0, 0, 0, 0, 0], "yolo_image": None}

        self._last_eth_ket   = None
        self._last_eth_xe    = None
        self.last_remote_jam = None
        self._last_uart_cmd  = None
        self._local_ready    = False   # True sau khi CNN xong, reset mỗi chu kỳ

    # =========================================================================
    # CẤU HÌNH & NHẬN LỆNH
    # =========================================================================

    def set_mode(self, mode):
        if mode not in ['single', 'branch']:
            print(f"[MODE] Không hợp lệ: {mode}")
            return False
        self.operation_mode = mode
        if mode == "branch":
            print("[SYSTEM] Chế độ Nhánh: Kích hoạt Ethernet.")
            self.eth.active = True
        else:
            print("[SYSTEM] Chế độ Đơn: Tắt Ethernet.")
            self.eth.active = False
            if self.eth.conn:
                try: self.eth.conn.close()
                except: pass
                self.eth.conn = None
        return True

    def uart_esp32_rasp(self, signal="run"):
        self.bien_run = True
        print("[UART] Nhận lệnh quét AI (run)")

    # =========================================================================
    # MODULE PHẦN CỨNG
    # =========================================================================

    def module_chup_anh(self):
        ret, frame = self.cam.read()
        if not ret or frame is None:
            return False
        self.frame_raw = frame
        self.frame_cnn, self.frame_yolo, self.brightness = \
            self.pre_proc.input_yolo_cnn(frame, skip_roi=False)
        return True

    def module_chay_cnn(self):
        if self.frame_cnn is None:
            return False
        status_local, conf, _ = self.cnn.predict(self.frame_cnn)
        self.ket_local = (status_local == "Ket Xe")
        self.frame_raw = self.cnn.draw_prediction(self.frame_raw, status_local, conf)
        cv2.imwrite(os.path.join(BASE_DIR, "static", "current_input.jpg"), self.frame_raw)
        return self.ket_local

    def module_chay_yolo(self):
        if self.frame_yolo is None:
            return 0
        self.yolo_results, self.xe_local = self.ai.detect(self.frame_yolo, self.brightness)
        if 'frame' in self.yolo_results:
            cv2.imwrite(os.path.join(BASE_DIR, "static", "current_yolo.jpg"), self.yolo_results['frame'])
        return self.xe_local

    # =========================================================================
    # UART SINGLE-SHOT
    # =========================================================================

    def _send_uart_single_shot(self, cmd):
        if cmd != self._last_uart_cmd:
            self.uart.send(cmd)
            self._last_uart_cmd = cmd
            print(f"[UART] → {cmd}")

    # =========================================================================
    # ETHERNET
    # Gửi kèm ready flag để handshake đồng bộ
    # =========================================================================

    def _eth_send_recv(self, force=False):
        """Gửi trạng thái local (kèm ready flag) và nhận trạng thái remote."""
        conn, k_rem, x_rem, rem_ready = False, False, 0, False
        if self.operation_mode == "single":
            return conn, k_rem, x_rem, rem_ready
        try:
            if force or self.ket_local != self._last_eth_ket or self.xe_local != self._last_eth_xe:
                self.eth.send_data(self.ket_local, self.xe_local, ready=self._local_ready)
                self._last_eth_ket = self.ket_local
                self._last_eth_xe  = self.xe_local
                print(f"[ETH] Gửi: ket={self.ket_local}, xe={self.xe_local}, ready={self._local_ready}")
            response = self.eth.get_remote_status()
            print(f"[ETH] Nhận: {response}")
            if isinstance(response, dict):
                k_rem     = response.get('ket', False)
                x_rem     = response.get('xe', 0)
                rem_ready = response.get('ready', False)
                conn      = True
        except Exception as e:
            print(f"[ETH] Lỗi: {e}")
        return conn, k_rem, x_rem, rem_ready

    def _sync_ethernet(self, force=False):
        """Wrapper tương thích — trả (conn, k_rem, x_rem)."""
        conn, k_rem, x_rem, _ = self._eth_send_recv(force=force)
        return conn, k_rem, x_rem

    # =========================================================================
    # HANDSHAKE ĐỒNG BỘ ĐẦU CHU KỲ
    # Chờ đến khi cả 2 bên đều ready (đã xong CNN)
    # =========================================================================

    def _cho_dong_bo(self, timeout=15):
    
        print(f"[{self.id}] Chờ đồng bộ remote (handshake)...")
        deadline = time.time() + timeout
        prev_k_rem = None

        while time.time() < deadline:
            conn, k_rem, x_rem, rem_ready = self._eth_send_recv(force=True)
            if conn and rem_ready:
                if k_rem == prev_k_rem:
                    print(f"[{self.id}] Handshake OK: ket={k_rem}, xe={x_rem}")
                    # Tắt ready ngay — one-shot, không để sót sang chu kỳ sau
                    self._local_ready = False
                    return k_rem, x_rem, True
                prev_k_rem = k_rem
            else:
                prev_k_rem = None
                print(f"[{self.id}] Chờ remote ready... rem_ready={rem_ready}")
            time.sleep(0.3)

        print(f"[{self.id}] Timeout handshake → chạy độc lập")
        self._local_ready = False
        return False, 0, False

    # =========================================================================
    # LOGIC ĐIỀU KHIỂN
    # =========================================================================

    def _esp32_mode(self, xe_count):
        if xe_count < 2:    return "m1"
        elif xe_count < 5: return "m2"
        elif xe_count < 8: return "m3"
        else:               return "m4"

    def logic_dieu_khien(self, ket_local, xe_local, ket_remote, xe_remote,
                         remote_connected, thoat_ket=False):
        if thoat_ket:
            return "a" if self.id == 'TRAM_A' else "b"

        if not remote_connected:
            if ket_local:
                return "A" if self.id == 'TRAM_A' else "B"
            return self._esp32_mode(xe_local)

        if self.id == 'TRAM_A':
            A, xe_a = ket_local,  xe_local
            B, xe_b = ket_remote, xe_remote
        else:
            B, xe_b = ket_local,  xe_local
            A, xe_a = ket_remote, xe_remote

        if A and B: return "A"
        if A:       return "A"
        if B:       return "B"
        return self._esp32_mode(max(xe_a, xe_b))

    # =========================================================================
    # MIRROR
    # =========================================================================

    def _xu_ly_mirror_remote(self, k_rem, x_rem, conn):
        if self.operation_mode != "branch":
            return
        if k_rem != self.last_remote_jam:
            thoat_ket = (self.last_remote_jam == True and k_rem == False)
            if thoat_ket:
                cmd = "b" if self.id == "TRAM_A" else "a"
            else:
                cmd = self.logic_dieu_khien(
                    self.ket_local, self.xe_local, k_rem, x_rem, conn
                )
            self._send_uart_single_shot(cmd)
            self.last_remote_jam = k_rem
            print(f"[MIRROR] xa {'kẹt' if k_rem else 'hết kẹt'} → gửi {cmd}")

    # =========================================================================
    # KHỐI CHÍNH
    # =========================================================================

    def thuc_thi_AI(self):

        if not self.bien_run:
            return None, None

        # =====================================================================
        # CHẾ ĐỘ SINGLE
        # =====================================================================
        if self.operation_mode == "single":
            print(f"[{self.id}] Single: bắt đầu...")

            if self.module_chup_anh():
                self.ket_local = self.module_chay_cnn()
            self.bien_run = False

            if self.ket_local:
                da_gui_ket = da_gui_thoat = False
                while True:
                    if self.module_chup_anh():
                        self.ket_local = self.module_chay_cnn()

                    if self.ket_local:
                        if not da_gui_ket:
                            cmd = self.logic_dieu_khien(self.ket_local, self.xe_local, False, 0, False)
                            self._send_uart_single_shot(cmd)
                            da_gui_ket = True; da_gui_thoat = False
                    else:
                        if not da_gui_thoat:
                            cmd = self.logic_dieu_khien(self.ket_local, self.xe_local, False, 0, False, thoat_ket=True)
                            self._send_uart_single_shot(cmd)
                            da_gui_thoat = True; da_gui_ket = False
                        if self.bien_run:
                            self.bien_run = False
                            self.xe_local = self.module_chay_yolo()           # chạy YOLO trước
                            cmd_final = self.logic_dieu_khien(False, self.xe_local, False, 0, False)
                            self._send_uart_single_shot(cmd_final)            # gửi mode cho ESP32
                            return self.result_AI(False, False, 0, cmd_final), cmd_final
                    time.sleep(1)

            self.xe_local = self.module_chay_yolo()
            cmd_final = self.logic_dieu_khien(self.ket_local, self.xe_local, False, 0, False)
            self._send_uart_single_shot(cmd_final)
            return self.result_AI(False, False, 0, cmd_final), cmd_final

        # =====================================================================
        # CHẾ ĐỘ BRANCH
        # =====================================================================
        print(f"[{self.id}] Branch: kiểm tra Ethernet...")

        try:
            response = self.eth.get_remote_status()
            if not isinstance(response, dict):
                print("[MODE] Branch: chưa kết nối, dừng.")
                self.bien_run = False
                return None, None
        except:
            print("[MODE] Branch: lỗi Ethernet, dừng.")
            self.bien_run = False
            return None, None

        # ── Bước 1: Reset ready, chạy CNN ────────────────────────────────────
        self._local_ready = False
        self._last_eth_ket = None   # Force gửi lại
        self._last_eth_xe  = None
        self.last_remote_jam = None

        if self.module_chup_anh():
            self.ket_local = self.module_chay_cnn()
        self.bien_run = False

        # ── Bước 2: Báo ready, chờ remote ready → handshake ─────────────────
        # Cả 2 phải xong CNN rồi mới cùng tra bảng logic
        self._local_ready = True
        k_rem, x_rem, conn = self._cho_dong_bo(timeout=1)

        # ── Bước 3: Tra bảng logic với trạng thái đầy đủ của cả 2 bên ───────
        cmd_logic = self.logic_dieu_khien(self.ket_local, self.xe_local, k_rem, x_rem, conn)
        print(f"[{self.id}] Tra bảng → {cmd_logic} | local={'KẸT' if self.ket_local else 'THOÁNG'} xa={'KẸT' if k_rem else 'THOÁNG'}")

        # ── NHÁNH KẸT (A hoặc B) → khóa vào luồng ưu tiên kẹt ─────────────
        if cmd_logic in ("A", "B"):
            print(f"[{self.id}] Vào luồng ưu tiên kẹt → {cmd_logic}")
            self._send_uart_single_shot(cmd_logic)
            da_gui_thoat = False
            cmd_thoat = None
            prev_k_rem = k_rem  # Theo dõi thay đổi trạng thái remote

            while True:
                if self.module_chup_anh():
                    self.ket_local = self.module_chay_cnn()

                conn, k_rem, x_rem = self._sync_ethernet(force=True)
                cmd_hien_tai = self.logic_dieu_khien(self.ket_local, self.xe_local, k_rem, x_rem, conn)

                if cmd_hien_tai in ("A", "B"):
                    self._send_uart_single_shot(cmd_hien_tai)
                    da_gui_thoat = False
                    prev_k_rem = k_rem
                else:
                    if not da_gui_thoat:
                        time.sleep(1)
                         # Sync lại để confirm cả 2 đều thấy hết kẹt
                        conn, k_rem, x_rem = self._sync_ethernet(force=True)
                        cmd_thoat = cmd_logic.lower()
                        self._send_uart_single_shot(cmd_thoat)
                        da_gui_thoat = True

                    self._local_ready = False
                    return self.result_AI(conn, k_rem, x_rem, cmd_thoat), cmd_thoat

                time.sleep(1)

        # ── NHÁNH CẢ 2 THOÁNG → cùng xuống YOLO đếm xe ─────────────────────
        print(f"[{self.id}] Cả 2 thoáng → YOLO...")
        self.xe_local = self.module_chay_yolo()
 
        # Handshake YOLO: báo ready, chờ Pi kia cũng xong YOLO rồi mới tra bảng
        # Dùng lại cơ chế ready — set True sau khi YOLO xong
        self._local_ready = True
        print(f"[{self.id}] Chờ remote xong YOLO...")
        deadline = time.time() + 15
        prev_x_rem = None
        conn, k_rem, x_rem = False, False, 0
        while time.time() < deadline:
            conn, k_rem, x_rem, rem_ready = self._eth_send_recv(force=True)
            if conn and rem_ready:
                if x_rem == prev_x_rem:   # Stable 2 lần liên tiếp
                    print(f"[{self.id}] YOLO sync OK: xe_local={self.xe_local}, xe_remote={x_rem}")
                    break
                prev_x_rem = x_rem
            else:
                prev_x_rem = None
            time.sleep(0.3)
        self._local_ready = False
 
        # Cả 2 đã có xe thật → tra bảng → cùng gửi cùng 1 lệnh
        cmd_final = self.logic_dieu_khien(self.ket_local, self.xe_local, k_rem, x_rem, conn)
        self._send_uart_single_shot(cmd_final)
        return self.result_AI(conn, k_rem, x_rem, cmd_final), cmd_final
 

    # =========================================================================
    # KẾT QUẢ
    # =========================================================================

    def result_AI(self, remote_connected, ket_remote, xe_remote, cmd):
        v = int(time.time() * 1000)
        return {
            "cnn_status":       "Ket Xe" if self.ket_local else "Thoang",
            "xe_local":         self.xe_local,
            "xe_remote":        xe_remote,
            "remote_jam":       ket_remote,
            "remote_connected": remote_connected,
            "brightness":       round(self.brightness, 2),
            "counts":           self.yolo_results.get("counts", [0, 0, 0, 0, 0]),
            "input_image":      f"/static/current_input.jpg?v={v}",
            "yolo_image":       f"/static/current_yolo.jpg?v={v}",
            "final_cmd":        cmd
        }