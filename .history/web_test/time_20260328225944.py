import time
import sys

class TrafficTimer:
    def __init__(self):
        self.start_time = None
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.start_time = time.time()
            self.is_running = True

    def reset(self):
        self.start_time = None
        self.is_running = False

    def get_elapsed(self):
        if not self.is_running:
            return 0
        return time.time() - self.start_time

    def show_debug(self, label, limit):
        elapsed = self.get_elapsed()
        # \r để ghi đè dòng cũ, flush để đẩy ra terminal ngay lập tức
        sys.stdout.write(f"\r[TIMER] {label}: {int(elapsed)}s / {limit}s    ")
        sys.stdout.flush()