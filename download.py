import torch
import ultralytics
import sys
import os

print("===== PYTHON =====")
print(sys.executable)
print(sys.version)

print("\n===== PYTORCH =====")
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only")

print("\n===== ULTRALYTICS =====")
print("Ultralytics version:", ultralytics.__version__)
print("Ultralytics path:", ultralytics.__file__)

print("\n===== CHECK MODULES =====")
from ultralytics.nn.tasks import DetectionModel

model = DetectionModel()
print("Modules in Ultralytics.nn.modules:")
import ultralytics.nn.modules as m
print([name for name in dir(m) if not name.startswith("_")])

print("\n===== CHECK nn MODULE =====")
import torch.nn as nn
print([name for name in dir(nn) if "Upsample" in name or "sample" in name])
