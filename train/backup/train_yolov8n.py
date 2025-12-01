# ============================================================
# 🎯 Train YOLOv8n (pretrained) với dataset của bạn
# ============================================================

from ultralytics import YOLO

# 1️⃣ Load model yolov8n.pt pretrained
#model = YOLO("yolov8n.pt") 
model = YOLO("my_yolov8n.yaml").load("yolov8n.pt")

# 2️⃣ Train model
model.train(
    task="detect",                     # Task: detect objects
    data="vehicle dataset/data.yaml",  # Đường dẫn file data.yaml
    epochs=2,                          # Số epoch 
    batch=16,                          # Batch size
    imgsz=640,                         # Image size
    device="cpu",                       # CPU hoặc "0" cho GPU
    save=True,                          # Lưu weight
    name="my_yolov8n_train_meme",            # Tên folder lưu kết quả
    exist_ok=True                       # Nếu folder tồn tại thì ghi đè
)#box_loss, cls_loss, dfl_loss
