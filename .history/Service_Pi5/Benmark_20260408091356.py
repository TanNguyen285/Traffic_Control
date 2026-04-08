import torch
import time
import numpy as np

def benchmark_model(
    model,
    input_size=(1, 3, 160, 160),
    device="cpu",
    num_runs=100,
    warmup=10
):
    """
    Benchmark FPS + latency cho mọi model PyTorch
    """

    device = torch.device(device)
    model = model.to(device)
    model.eval()

    # tạo input giả
    dummy = torch.randn(*input_size).to(device)

    # ===== warmup =====
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(dummy)

    # ===== benchmark =====
    times = []

    with torch.no_grad():
        for _ in range(num_runs):
            start = time.time()
            _ = model(dummy)
            end = time.time()

            times.append(end - start)

    # ===== tính toán =====
    times = np.array(times)
    avg_time = times.mean()
    fps = 1.0 / avg_time
    latency_ms = avg_time * 1000

    print("===== BENCHMARK RESULT =====")
    print(f"Device: {device}")
    print(f"Input size: {input_size}")
    print(f"Runs: {num_runs}")
    print(f"FPS: {fps:.2f}")
    print(f"Latency: {latency_ms:.2f} ms")
    print(f"Min latency: {times.min()*1000:.2f} ms")
    print(f"Max latency: {times.max()*1000:.2f} ms")

    return fps, latency_ms