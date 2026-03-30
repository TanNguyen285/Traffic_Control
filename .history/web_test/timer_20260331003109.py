import time
import sys
import json
import os

class Timer_tram:
    def __init__(self, name="default"):
        self.name = name
        self.filename = f"timer_{self.name}.json"
        self.start_time = None
        self.is_running = False
        self.load_from_json() # Tự động hồi phục trạng thái khi khởi tạo

    def load_from_json(self):
        """Đọc trạng thái cũ từ file JSON"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.start_time = data.get("start_time")
                    self.is_running = data.get("is_running", False)
            except:
                self.reset()

    def save_to_json(self):
        """Lưu trạng thái hiện tại vào JSON"""
        with open(self.filename, 'w') as f:
            json.dump({class Timer_tram:
    def __init__(self):
        self.start_time = None

    def start(self):
        if self.start_time is None:
            self.start_time = time.time()

    def reset(self):
        self.start_time = None

    def get_elapsed(self):
        if self.start_time is None:
            return 0
        return time.time() - self.start_time
                "start_time": self.start_time,
                "is_running": self.is_running,
                "last_update": time.time()
            }, f, indent=4)

    def start(self):
        if not self.is_running:
            self.start_time = time.time()
            self.is_running = True
            self.save_to_json()

    def reset(self):
        self.start_time = None
        self.is_running = False
        if os.path.exists(self.filename):
            os.remove(self.filename) # Xóa file khi hết kẹt

    def get_elapsed(self):
        if not self.is_running or self.start_time is None:
            return 0
        return time.time() - self.start_time

    def show_debug(self, label, limit):
        elapsed = self.get_elapsed()
        # Hiển thị ghi đè dòng cũ
        sys.stdout.write(f"\r[TIMER] {label}: {int(elapsed)}s / {limit}s    ")
        sys.stdout.flush()
        
        # Cập nhật JSON liên tục để nếu Pi có sập nguồn vẫn không mất giây
        self.save_to_json()