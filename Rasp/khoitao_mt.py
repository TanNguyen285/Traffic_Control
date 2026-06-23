import torch
import socket
import subprocess
from ultralytics import YOLO
from torchvision import transforms

from camera import Camera
from yolov26 import Yolo_AI
from uart_service import UART_config
from tienxulyanh import Tienxulyanh
from logic_fix import TrafficLogic
from cnn_onnx import Simple_CNN_config
from ethernet import EthernetService
from ROI import ROIManager


# ─────────────────────────────────────────────────────────────────────────────
# CẤU HÌNH HỆ THỐNG
# ─────────────────────────────────────────────────────────────────────────────
class Config:
    YOLO_PATH   = "runs/Yolo/best_ncnn_model"
    CNN_PATH    = "runs/Anpha/simple_anpha.onnx"
    SCI_PATH    = "runs/SCI/difficult.pt"
    DEVICE      = torch.device("cpu")
    CNN_CLASSES = ["Thong Thoang", "Ket Xe"]
    YOLO_CLASSES = ['car', 'van', 'bus', 'motorcycle', 'truck']
    ROI = [
        [20,  640],
        [220,  20],
        [420,  20],
        [620, 640],
    ]
    MY_PORT = 9999


# ─────────────────────────────────────────────────────────────────────────────
# KHỞI TẠO HỆ THỐNG
# ─────────────────────────────────────────────────────────────────────────────
def init_system():
    # 1. Nhận diện trạm theo hostname
    h_name = socket.gethostname().lower()
    if h_name == 'lagct':
        s_id       = 'TRAM_A'
        p_hostname = 'lagct2.local'
    else:
        s_id       = 'TRAM_B'
        p_hostname = 'lagct.local'

    print(f"[SYSTEM] Khởi động {s_id} — peer: {p_hostname}")

    # 2. Ethernet
    eth_service = EthernetService(
        station_id=s_id,
        peer_hostname=p_hostname,
        port=Config.MY_PORT,
    )

    # 3. Hardware
    cam  = Camera(src=0)
    cam.start()
    uart = UART_config(port="/dev/ttyAMA0", baudrate=115200)

    # 4. ROI — 1 instance duy nhất, dùng chung cho AI lẫn web stream
    #    Nếu roi_config.json đã tồn tại (user đã vẽ tay) thì ROIManager
    #    tự load file đó, bỏ qua polygon_pts mặc định bên dưới.
    ROI_lane = ROIManager(polygon_pts=Config.ROI)

    # 5. Pre-processing — truyền roi_manager để share cùng polygon
    #    Web chỉnh ROI → save_points() → AI áp dụng ngay, không restart
    pre_proc = Tienxulyanh(
        sci_path=Config.SCI_PATH,
        target_size=(480, 480),
        use_sci=True,
        roi_manager=ROI_lane,
    )

    # 6. YOLO
    yolo_model = YOLO(Config.YOLO_PATH)
    ai_yolo    = Yolo_AI(yolo_model, class_names=Config.YOLO_CLASSES)

    # 7. CNN
    cnn_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std =[0.229, 0.224, 0.225],
        ),
    ])
    cnn_service = Simple_CNN_config(
        model_path=Config.CNN_PATH,
        transform=cnn_transform,
        classes=Config.CNN_CLASSES,
    )

    # 8. Traffic Engine
    engine = TrafficLogic(
        yolo_ai=ai_yolo,
        cnn_service=cnn_service,
        pre_proc=pre_proc,
        uart=uart,
        cam=cam,
        eth_service=eth_service,
        station_id=s_id,
    )

    # 9. UART callback
    uart.start_listening(engine.uart_esp32_rasp)

    # 10. CPU performance mode
    _set_cpu_performance()

    return engine, cam, Config, ROI_lane


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _set_cpu_performance():
    cmd = ("echo performance | "
           "sudo -S tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor")
    try:
        subprocess.run(
            cmd,
            shell=True,
            input="a\n",          # sudo password
            text=True,
            capture_output=True,
        )
        print("[SYSTEM] CPU governor: performance mode")
    except Exception as e:
        print(f"[SYSTEM] Lỗi kích hoạt performance mode: {e}")