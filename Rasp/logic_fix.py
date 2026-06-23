import os
import time
import cv2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam,
                 eth_service, station_id='TRAM_A'):
        self.ai       = yolo_ai
        self.cnn      = cnn_service
        self.pre_proc = pre_proc
        self.uart     = uart
        self.cam      = cam
        self.eth      = eth_service
        self.id       = station_id.upper()

        self.bien_run       = False
        self.bien_run1      = False
        self.operation_mode = "single"

        self.frame_raw    = None
        self.frame_cnn    = None
        self.frame_yolo   = None
        self.brightness   = 0
        self.ket_local    = False
        self.xe_local     = 0
        self.yolo_results = {"counts": [0, 0, 0, 0, 0], "yolo_image": None}
        self.frame_enhanced = None
        self._last_uart_cmd = None

    def set_mode(self, mode: str) -> bool:
        if mode not in ('single', 'branch'):
            print(f"[MODE] Không hợp lệ: {mode}")
            return False
        self.operation_mode = mode
        print(f"[SYSTEM] Chế độ: {mode}")
        if mode == 'branch':
            self.eth.start()
        return True

    def uart_esp32_rasp(self, signal: str = "run"):
        if signal == "run1":
            self.bien_run1 = True
            print("[UART] Nhận lệnh thoát kẹt khẩn cấp (run1)")
        else:
            self.bien_run = True
            print("[UART] Nhận lệnh quét AI (run)")

    def module_chup_anh(self) -> bool:
        ret, frame = self.cam.read()
        if not ret or frame is None:
            return False
        self.frame_raw = frame
        self.frame_cnn, self.frame_yolo, self.frame_enhanced, self.brightness = \
            self.pre_proc.input_yolo_cnn(frame, skip_roi=False)
        return True

    def module_chay_cnn(self) -> bool:
        if self.frame_cnn is None:
            return False
        status_local, conf, _ = self.cnn.predict(self.frame_cnn)
        self.ket_local = (status_local == "Ket Xe")
        # Dùng frame_enhanced thay frame_raw để hiển thị ảnh đã làm sáng
        display_frame = self.frame_enhanced if self.frame_enhanced is not None else self.frame_raw
        display_frame = self.cnn.draw_prediction(display_frame, status_local, conf)
        cv2.imwrite(os.path.join(BASE_DIR, "static", "current_input.jpg"), display_frame)
        return self.ket_local

    def module_chay_yolo(self) -> int:
        if self.frame_yolo is None:
            return 0
        self.yolo_results, self.xe_local = self.ai.detect(self.frame_yolo, self.brightness)
        if 'frame' in self.yolo_results:
            cv2.imwrite(os.path.join(BASE_DIR, "static", "current_yolo.jpg"),
                        self.yolo_results['frame'])
        return self.xe_local

    def _send_uart(self, cmd: str):
        if cmd != self._last_uart_cmd:
            self.uart.send(cmd)
            self._last_uart_cmd = cmd
            print(f"[UART] → {cmd}")

    def _esp32_mode(self, xe_count: int) -> str:
        if xe_count < 2:   return "m1"
        elif xe_count < 5: return "m2"
        elif xe_count < 8: return "m3"
        else:              return "m4"

    def logic_dieu_khien(self, ket_main: bool, xe_main: int,
                         ket_nhanh: bool, xe_nhanh: int,
                         remote_connected: bool) -> str:
        if not remote_connected:
            if ket_main:
                return "A" if self.id == 'TRAM_A' else "B"
            return self._esp32_mode(xe_main)

        if self.id == 'TRAM_A':
            A, xe_a = ket_main,  xe_main
            B, xe_b = ket_nhanh, xe_nhanh
        else:
            B, xe_b = ket_main,  xe_main
            A, xe_a = ket_nhanh, xe_nhanh

        if A and B: return "A"
        if A:       return "A"
        if B:       return "B"
        return self._esp32_mode(max(xe_a, xe_b))

    def _handshake(self, timeout: float = 10.0, stage: str = ""):
        print(f"[{self.id}] Handshake [{stage}] bắt đầu...")
        self.eth.send(self.ket_local, self.xe_local, ready=True, stage=stage)

        data = self.eth.wait_fresh(timeout=timeout, expected_stage=stage)
        if data is None:
            print(f"[{self.id}] Handshake [{stage}] TIMEOUT")
            return None, None, False

        ket_r = data.get('CNN', False)
        xe_r  = data.get('xe',  0)
        print(f"[{self.id}] Handshake [{stage}] OK — remote: ket={ket_r}, xe={xe_r}")
        return ket_r, xe_r, True

    def thuc_thi_AI(self):
        if not self.bien_run:
            return None, None
        if self.operation_mode == "single":
            return self._single_mode()
        return self._branch_mode()

    def _single_mode(self):
        print(f"[{self.id}] Single: bắt đầu...")
        if self.module_chup_anh():
            self.ket_local = self.module_chay_cnn()
        self.bien_run = False

        if self.ket_local:
            result = self._single_loop_ket()
            if result is not None:
                return result

        self.xe_local = self.module_chay_yolo()
        cmd = self.logic_dieu_khien(self.ket_local, self.xe_local, False, 0, False)
        self._send_uart(cmd)
        return self.result_AI(False, False, 0, cmd), cmd

    def _single_loop_ket(self):
        da_gui_ket = da_gui_thoat = False
        while True:
            if self.bien_run1:
                self.bien_run1 = False
                self._last_uart_cmd = None
                self._send_uart("m2")
                print(f"[{self.id}] run1 → thoát kẹt khẩn cấp")
                return self.result_AI(False, False, 0, "m2", is_emergency=True), "m2"

            if self.module_chup_anh():
                self.ket_local = self.module_chay_cnn()

            if self.ket_local:
                if not da_gui_ket:
                    cmd = self.logic_dieu_khien(self.ket_local, self.xe_local, False, 0, False)
                    self._send_uart(cmd)
                    da_gui_ket = True
                    da_gui_thoat = False
            else:
                if not da_gui_thoat:
                    cmd_ket   = self.logic_dieu_khien(True, self.xe_local, False, 0, False)
                    cmd_thoat = cmd_ket.lower()
                    self._send_uart(cmd_thoat)
                    da_gui_thoat = True
                    da_gui_ket   = False
                if self.bien_run:
                    self.bien_run = False
                    self.xe_local = self.module_chay_yolo()
                    cmd_final = self.logic_dieu_khien(False, self.xe_local, False, 0, False)
                    self._send_uart(cmd_final)
                    return self.result_AI(False, False, 0, cmd_final), cmd_final

            time.sleep(1)

    def _branch_mode(self):
        print(f"[{self.id}] Branch: bắt đầu...")
        if not self.eth.connected:
            print(f"[{self.id}] Ethernet chưa kết nối → dừng.")
            self.bien_run = False
            return None, None

        self.xe_local = 0
        self.bien_run = False

        if self.module_chup_anh():
            self.ket_local = self.module_chay_cnn()

        ket_nhanh, xe_nhanh, conn = self._handshake(timeout=10, stage="CNN")
        if not conn:
            print(f"[{self.id}] Handshake CNN thất bại → dừng.")
            return None, None

        cmd_logic = self.logic_dieu_khien(self.ket_local, self.xe_local, ket_nhanh, xe_nhanh, conn)
        print(f"[{self.id}] Tra bảng → {cmd_logic} | "
              f"local={'KẸT' if self.ket_local else 'THOÁNG'} "
              f"xa={'KẸT' if ket_nhanh else 'THOÁNG'}")

        if cmd_logic in ("A", "B"):
            return self._branch_loop_ket(cmd_logic, ket_nhanh, xe_nhanh, conn)
        else:
            return self._branch_yolo(ket_nhanh, xe_nhanh, conn)

    def _branch_loop_ket(self, cmd_ket: str, ket_nhanh: bool, xe_nhanh: int, conn: bool):
        self._last_uart_cmd = None
        self._send_uart(cmd_ket)

        i_am_jammed = (
            (cmd_ket == "A" and self.id == "TRAM_A") or
            (cmd_ket == "B" and self.id == "TRAM_B")
        )
        if i_am_jammed:
            return self._loop_tram_ket(cmd_ket, ket_nhanh, xe_nhanh, conn)
        else:
            return self._loop_tram_cho(cmd_ket, ket_nhanh, xe_nhanh, conn)

    def _loop_tram_ket(self, cmd_ket: str, ket_nhanh: bool, xe_nhanh: int, conn: bool):
        print(f"[{self.id}] Tôi kẹt → loop CNN...")
        while True:
            if self.bien_run1:
                self.bien_run1 = False
                self._last_uart_cmd = None
                self._send_uart("m2")
                self.eth.clear()
                return self.result_AI(conn, ket_nhanh, xe_nhanh, "m2", is_emergency=True), "m2"

            if self.module_chup_anh():
                self.ket_local = self.module_chay_cnn()

            if not self.ket_local:
                print(f"[{self.id}] Hết kẹt → handshake thoát...")
                ket_nhanh, xe_nhanh, conn = self._handshake(timeout=10, stage="THOAT")
                if ket_nhanh is None:
                    print(f"[{self.id}] Handshake thoát timeout → gửi lệnh thoát và dừng.")
                    ket_nhanh, xe_nhanh, conn = False, 0, False

                cmd_thoat = cmd_ket.lower()
                self._last_uart_cmd = None
                self._send_uart(cmd_thoat)
                self.eth.clear()
                print(f"[{self.id}] Gửi lệnh thoát {cmd_thoat} → kết thúc.")
                return self.result_AI(conn, ket_nhanh, xe_nhanh, cmd_thoat), cmd_thoat

            time.sleep(1)

    def _loop_tram_cho(self, cmd_ket: str, ket_nhanh: bool, xe_nhanh: int, conn: bool):
        print(f"[{self.id}] Bên kia kẹt → chờ handshake thoát...")
        deadline = time.time() + 155
        while True:
            if self.bien_run1:
                self.bien_run1 = False
                self._last_uart_cmd = None
                self._send_uart("m2")
                self.eth.clear()
                return self.result_AI(conn, ket_nhanh, xe_nhanh, "m2", is_emergency=True), "m2"

            remaining = deadline - time.time()
            if remaining <= 0:
                print(f"[{self.id}] Timeout chờ thoát → dừng.")
                return None, None

            # Chờ từng chunk nhỏ để check bien_run1 thường xuyên
            ket_nhanh, xe_nhanh, conn = self._handshake(timeout=min(1.0, remaining), stage="THOAT")
            if ket_nhanh is None:
                continue  # chưa nhận được → loop lại check bien_run1 rồi chờ tiếp

            cmd_thoat = cmd_ket.lower()
            self._last_uart_cmd = None
            self._send_uart(cmd_thoat)
            self.eth.clear()
            print(f"[{self.id}] Gửi lệnh thoát {cmd_thoat} → kết thúc.")
            return self.result_AI(conn, ket_nhanh, xe_nhanh, cmd_thoat), cmd_thoat

    def _branch_yolo(self, ket_nhanh: bool, xe_nhanh: int, conn: bool):
        print(f"[{self.id}] Cả 2 thoáng → YOLO...")
        self.xe_local = self.module_chay_yolo()

        ket_nhanh, xe_nhanh, conn = self._handshake(timeout=15, stage="YOLO")
        if not conn:
            print(f"[{self.id}] Handshake YOLO thất bại → dừng.")
            return None, None

        cmd_final = self.logic_dieu_khien(self.ket_local, self.xe_local, ket_nhanh, xe_nhanh, conn)
        self._last_uart_cmd = None
        self._send_uart(cmd_final)
        self.eth.clear()
        print(f"[{self.id}] YOLO → {cmd_final} (local xe={self.xe_local}, remote xe={xe_nhanh})")
        return self.result_AI(conn, ket_nhanh, xe_nhanh, cmd_final), cmd_final

    def result_AI(self, remote_connected: bool, ket_remote: bool,
                  xe_remote: int, cmd: str, is_emergency: bool = False) -> dict:
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
            "final_cmd":        cmd,
            "is_emergency":     is_emergency
        }