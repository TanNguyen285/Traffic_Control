class Timer:
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