import time
import os
import json
import numpy as np

class UnifiedBenchmark:
    def __init__(self, log_file="ket_qua_ai.json"):
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Tự động lấy đường dẫn tuyệt đối để lưu file JSON vào đúng thư mục benchmark
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.log_path = os.path.join(self.base_path, log_file)

    def save_to_json(self, label, avg_ms, fps, size):
        data = {}
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                try: data = json.load(f)
                except: data = {}

        data[label] = {
            "latency_ms": round(avg_ms, 2),
            "fps": round(fps, 2),
            "input_size": str(size),
            "device": self.device,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(self.log_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"✅ Đã lưu '{label}' vào: {self.log_path}")