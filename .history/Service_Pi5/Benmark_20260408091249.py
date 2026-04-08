import torch
import time
from your_model_file import SimpleCNN

# ===== CONFIG =====
IMG_SIZE = 160
NUM_RUNS = 100   # số lần đo
WARMUP = 10      # bỏ qua 10 lần đầu

# ===== LOAD MODEL =====
model = SimpleCNN(num_classes=2)
model.load_state_dict(torch.load("model.pt", map_location="cpu"))
model.eval()

# ===== INPUT =====
dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)

# ===== WARMUP =====
with torch.no_grad():
    for _ in range(WARMUP):
        _ = model(dummy)

# ===== BENCHMARK =====
start = time.time()

with torch.no_grad():
    for _ in range(NUM_RUNS):
        _ = model(dummy)

end = time.time()

# ===== RESULT =====
total_time = end - start
fps = NUM_RUNS / total_time
latency = (total_time / NUM_RUNS) * 1000  # ms

print(f"FPS: {fps:.2f}")
print(f"Latency: {latency:.2f} ms")