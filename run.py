# ============================================================
# 🎥 Test YOLOv8 model trên video MP4 (live, show class + confidence)
# ============================================================

from ultralytics import YOLO
import cv2

# 1️⃣ Load model đã train hoặc pretrained
model = YOLO("runs/detect/my_yolov8n_train/weights/best.pt")  

# 2️⃣ Đường dẫn video input
video_path = "C:\\Users\\DELL\\Documents\\PlatformIO\\.vscode\\doan2_CNN\\CNN_AI\\CNN_AI\\Input\\test_2.mp4"

# 3️⃣ Mở video
cap = cv2.VideoCapture(video_path)
window_name = "YOLOv8 Test"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, 960, 540)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 🔹 Dự đoán frame
    results = model(frame, conf=0.4,iou=0.5)  # conf thấp để hiện nhiều bbox

    # 🔹 Lấy frame đã vẽ bbox
    frame_out = results[0].plot()  

    # 🔹 Vẽ class + confidence thủ công
    for box in results[0].boxes:  # boxes là list bounding boxes
        cls_id = int(box.cls[0])      # class index
        conf   = float(box.conf[0])   # confidence
        label  = f"{results[0].names[cls_id]} {conf:.2f}"

        # 🔹 Lấy tọa độ box
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.putText(
            frame_out,
            label,
            (x1, y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA
        )

    # 🔹 Hiển thị
    cv2.imshow(window_name, frame_out)

    # 🔹 ESC để thoát
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
