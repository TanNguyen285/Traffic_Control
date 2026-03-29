import torch
import torch.nn.functional as F
from PIL import Image
import cv2
import base64
import time

class TrafficLogic:
    def __init__(self, yolo_ai, cnn_model, cnn_transform, cnn_classes, device, pre_proc, uart, cam, 
                 station_id='A', 
                 # ==========================================
                 # CONFIGURATION: Tùy chỉnh thời gian các Mode
                 # ==========================================
                 t_m1=15,    # Xanh mode 1
                 t_m2=20,    # Xanh mode 2
                 t_m3=25,    # Xanh mode 3
                 t_m4=40,    # Xanh mode 4
                 t_m_ket=60, # Xanh khi kẹt xe
                 t_y=3       # Vàng mặc định
                 ):
        
        self.ai = yolo_ai
        self.cnn_net = cnn_model
        self.cnn_transform = cnn_transform
        self.cnn_classes = cnn_classes
        self.device = device
        self.pre_proc = pre_proc
        self.uart = uart
        self.cam = cam
        self.id = station_id.upper()

        # Lưu cấu hình vào dict
        self.t_modes = {
            'm1': t_m1, 'm2': t_m2, 'm3': t_m3, 'm4': t_m4, 'xa_ket': t_m_ket
        }
        self.yellow_duration = t_y
        
        # Khởi tạo trạng thái ban đầu
        self.current_phase = 'red'
        self.phase_start_time = time.time()
        self.t_cho = 0

        # Mặc định ban đầu chạy m1
        self.green_duration = self.t_modes['m1']
        # Công thức: t_r = t_m + t_y
        self.red_duration = self.green_duration + self.yellow_duration

    def _phase_elapsed(self):
        return time.time() - self.phase_start_time

    def remaining_phase_time(self, phase=None):
        phase = phase or self.current_phase
        duration = {
            'red': self.red_duration,
            'green': self.green_duration,
            'yellow': self.yellow_duration
        }.get(phase, 0)
        return max(0, duration - self._phase_elapsed() if phase == self.current_phase else 0)

    def _advance_phase(self):
        """Chuyển pha và cập nhật t_r theo t_m mới nhất đã quét được"""
        elapsed = self._phase_elapsed()
        
        # Lấy duration của pha hiện tại
        current_dur = {
            'red': self.red_duration,
            'green': self.green_duration,
            'yellow': self.yellow_duration
        }[self.current_phase]

        if elapsed >= current_dur:
            if self.current_phase == 'red':
                self.current_phase = 'green'
            elif self.current_phase == 'green':
                self.current_phase = 'yellow'
            else: # yellow -> red
                self.current_phase = 'red'
                # Khi bắt đầu pha Đỏ, cập nhật t_r dựa trên t_m vừa chạy hoặc vừa quét
                self.red_duration = self.green_duration + self.yellow_duration
            
            self.phase_start_time = time.time()

    def should_run_yolo(self):
        """Quét YOLO ở cuối pha Đỏ để quyết định t_m cho pha Xanh sắp tới"""
        self._advance_phase()
        if self.current_phase == 'yellow': return False
        
        rem = self.remaining_phase_time()
        # Quét trước khi chuyển pha 2-5 giây để kịp xử lý logic
        if self.current_phase == 'red' and 5 >= rem > 2: return True
        if self.current_phase == 'green' and rem <= 2: return True
        return False

    def update_timing_by_mode(self, n, is_ket=False):
        """Logic cốt lõi: Chọn Mode -> Chọn t_m -> Tính t_r"""
        if is_ket:
            mode = 'xa_ket'
        elif n < 5: mode = 'm1'
        elif n <= 10: mode = 'm2'
        elif n <= 15: mode = 'm3'
        else: mode = 'm4'
        
        # Cập nhật t_m (green)
        self.green_duration = self.t_modes[mode]
        # Cập nhật t_r theo công thức t_r = t_m + t_y
        self.red_duration = self.green_duration + self.yellow_duration
        
        return mode

    def _detect_frame(self, frame_raw, remote_data=None):
        if frame_raw is None: return {'error': 'No Frame'}

        # 1. Tiền xử lý & CNN
        frame_cnn, frame_yolo, brightness = self.pre_proc.process_dual(frame_raw, roi_box=[0.1, 0.9, 0.0, 1.0])
        status_local, conf_local = self.predict_cnn(frame_cnn)
        ket_local = (status_local == 'Ket Xe')

        xe_local = 0
        yolo_data = {}

        # 2. Chạy YOLO và cập nhật Thời gian/Mode
        if self.should_run_yolo():
            yolo_result, xe_local = self.ai.detect(frame_yolo, brightness)
            if isinstance(yolo_result, dict): yolo_data = yolo_result
            
            # Cập nhật t_m và t_r ngay lập tức dựa trên số xe vừa quét
            self.update_timing_by_mode(xe_local, is_ket=ket_local)

        # 3. Logic điều khiển (giữ nguyên cấu trúc của bạn)
        # Giả định Station A và B gửi dữ liệu cho nhau
        cmd = 'm1'
        note = ''
        
        # Phân xử A/B để ghi đè lệnh UART (nếu cần)
        if ket_local:
            cmd = f"{self.id.lower()}_xa"
            note = "Phát hiện kẹt xe tại chỗ"
        else:
            # Lấy mode tương ứng với số xe
            for m_name, m_val in self.t_modes.items():
                if m_val == self.green_duration:
                    cmd = m_name
                    break
            note = f"Chạy theo mật độ xe: {xe_local}"

        # 4. Trả về kết quả
        _, buf = cv2.imencode('.jpg', frame_yolo)
        img_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

        result = {
            'light': self.current_phase,
            'cmd': cmd,
            't_m_hien_tai': self.green_duration,
            't_r_hien_tai': self.red_duration,
            'green_time': int(self.remaining_phase_time('green')),
            'red_time': int(self.remaining_phase_time('red')),
            'yellow_time': int(self.remaining_phase_time('yellow')),
            'note': note,
            'total_vehicles': xe_local,
            'processed_image': img_b64
        }

        if self.uart:
            try: self.uart.send(cmd)
            except: pass
            
        return result

    def predict_cnn(self, frame_cv2):
        # (Giữ nguyên hàm predict_cnn của bạn ở đây)
        pass