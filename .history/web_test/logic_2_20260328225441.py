import cv2
import base64
import time
import sys # Thêm sys để flush terminal

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_service, pre_proc, uart, cam, eth_service, station_id='A',
                 t_m1=15, t_m2=20, t_m3=25, t_m4=40, t_ket=150, t_y=3):
        
        self.ai = yolo_ai            
        self.cnn = cnn_service      
        self.pre_proc = pre_proc    
        self.uart = uart
        self.cam = cam
        self.eth = eth_service 
        self.id = station_id.upper()
        
        self.is_jamming = False      
        self.jam_start_time = 0      
        self.last_relief_time = 0    
        self.in_relief_mode = False  
        
        self.t_ket_limit = t_ket       # 150s
        self.t_relief = 20           # 20s cứu trạm B
        self.t_modes = {'m1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'A': t_ket}
        self.t_y = t_y

    def AI_CNN_SCI(self, selected_image=None):
        frame_raw = selected_image if selected_image is not None else self.cam.read()[1]
        if frame_raw is None: return {"error": "No Frame"}, "m0"

        input_image_url = self._to_base64_url(frame_raw)
        frame_cnn, frame_yolo, brightness = self.pre_proc.input_yolo_cnn(frame_raw, skip_roi=(selected_image is not None))

        # --- CNN QUÉT LIÊN TỤC ---
        status_local, _, _ = self.cnn.predict(frame_cnn)
        is_jam_now = (status_local == "Ket Xe")
        curr_time = time.time()

        if is_jam_now:
            if not self.is_jamming:
                self.is_jamming = True
                self.jam_start_time = curr_time
                self.in_relief_mode = False
                print(f"\n[PHÁT HIỆN KẸT] Bắt đầu xả Trạm {self.id}...")

            elapsed_jam = curr_time - self.jam_start_time
            
            # Kiểm tra cứu trạm B (m2)
            if not self.in_relief_mode and elapsed_jam > self.t_ket_limit:
                self.in_relief_mode = True
                self.last_relief_time = curr_time
                cmd = "m2"
            elif self.in_relief_mode:
                elapsed_relief = curr_time - self.last_relief_time
                if elapsed_relief < self.t_relief:
                    cmd = "m2"
                    # In đè dòng đếm ngược cứu trạm B
                    sys.stdout.write(f"\r[DEBUG] Đang cứu trạm B: {int(self.t_relief - elapsed_relief)}s còn lại...   ")
                    sys.stdout.flush()
                else:
                    self.in_relief_mode = False
                    self.jam_start_time = curr_time # Reset mốc 150s
                    cmd = "A"
                    print(f"\n[HẾT 20S] Quay lại xả kẹt trạm {self.id}.")
            else:
                cmd = "A"
                # In đè dòng đếm thời gian đã kẹt của trạm A
                sys.stdout.write(f"\r[DEBUG] Đang xả kẹt {self.id}: Đã trôi qua {int(elapsed_jam)}s / {self.t_ket_limit}s   ")
                sys.stdout.flush()

            self.uart.send(cmd)
            self.eth.send_data(True, 0)
            return self._build_result(status_local, 0, brightness, input_image_url), cmd

        # --- KHI HẾT KẸT (BINH THUONG) ---
        else:
            if self.is_jamming:
                print(f"\n[CNN] HẾT KẸT! Chờ 5s chuyển trạng thái...")
                time.sleep(5)
                self.is_jamming = False
                self.in_relief_mode = False

            yolo_res, xe_local = self.ai.detect(frame_yolo, brightness)
            self.eth.send_data(False, xe_local)
            
            remote_data = self.eth.get_remote_status()
            xe_remote = remote_data.get('xe', 0)
            xe_max = max(xe_local, xe_remote)
            t_m, cmd = self._esp32_mode(xe_max)
            
            # In đè trạng thái YOLO
            sys.stdout.write(f"\r[YOLO MODE] Xe Local: {xe_local} | Remote: {xe_remote} | Lệnh: {cmd} ({t_m}s)   ")
            sys.stdout.flush()

            self.uart.send(cmd)
            return self._build_result(status_local, xe_local, brightness, input_image_url), cmd

    def _esp32_mode(self, total):
        if total < 5: return self.t_modes['m1'], "m1"
        elif total <= 10: return self.t_modes['m2'], "m2"
        elif total <= 20: return self.t_modes['m3'], "m3"
        return self.t_modes['m4'], "m4"

    def _build_result(self, status, xe, bright, url):
        return {"cnn_status": status, "xe_local": xe, "brightness": round(bright, 2), "input_image": url}

    def _to_base64_url(self, frame):
        _, buf = cv2.imencode('.jpg', frame)
        return f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"