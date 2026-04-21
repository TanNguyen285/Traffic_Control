
import torch
from ultralytics import YOLO
from torchvision import transforms
from SimpleCNN.custom import SimpleCNN
import socket

# Import các Class của bạn
from camera import Camera
from yolov26 import Yolo_AI
from uart_service import UART_config
from tienxulyanh import Tienxulyanh
from logic_test import TrafficLogic
from cnn_onnx import Simple_CNN_config
from ethernet import EthernetService
from ROI import ROIManager

class Config:
    YOLO_PATH = "runs/detect/best_ncnn_model"
    # CNN_PATH = "runs/exp3/best_cnn_model.pth"
    CNN_PATH = "runs/exp3/simple_cnn.onnx"  # Đường dẫn mới cho mô hình CNN đã chuyển sang ONNX
    SCI_PATH = "web_test/weights/difficult.pt"
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    CNN_CLASSES = ["Thong Thoang", "Ket Xe"]
    YOLO_CLASSES = ['car', 'van', 'bus', 'motorcycle', 'truck']
    ROI = [
        [20, 640],   # 1. Đáy trái: Sát mép trái và dưới cùng (Rộng ra)
        [220, 20],   # 2. Đỉnh trái: Đẩy lên rất cao và hơi rộng ra (Dài ra)
        [420, 20],   # 3. Đỉnh phải: Đối xứng với đỉnh trái (Dài ra)
        [620, 640]   # 4. Đáy phải: Sát mép phải và dưới cùng (Rộng ra)
    ]

def init_system():
    h_name = socket.gethostname().lower()
    
    # --- CẤU HÌNH TẬP TRUNG TẠI ĐÂY ---
    MY_PORT = 9999  # Cổng mặc định cho EthernetService, có thể thay đổi nếu cần
    # ----------------------------------

    if h_name == 'lagct':
        s_id = 'TRAM_A'
        p_hostname = 'lagct2.local'
    else:
        s_id = 'TRAM_B'
        p_hostname = 'lagct.local'

    # Truyền biến MY_PORT vào Class
    eth_service = EthernetService(station_id=s_id, peer_hostname=p_hostname, port=MY_PORT)

    # Hardware
    cam = Camera(src=0) 
    cam.start()
    uart = UART_config(port="/dev/ttyAMA0", baudrate=115200)
    
    # 2.1 Khởi tạo ROIManager để vẽ hiển thị
    ROI_lane = ROIManager(polygon_pts=Config.ROI)

    # 2.2 Pre-processing
    pre_proc = Tienxulyanh(
        sci_path=Config.SCI_PATH, 
        target_size=(640, 640), 
        use_sci=True,
        polygon_pts=Config.ROI
    )

    # 3. YOLO AI
    yolo_model = YOLO(Config.YOLO_PATH)
    ai_yolo = Yolo_AI(yolo_model, class_names=Config.YOLO_CLASSES)

    # 4. CNN Service
    #cnn_net = SimpleCNN(num_classes=2).to(Config.DEVICE)
    #cnn_net.load_state_dict(torch.load(Config.CNN_PATH, map_location=Config.DEVICE))
    #cnn_net.eval()
    
    cnn_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    cnn_service = Simple_CNN_config(
        #model=cnn_net, 
        model_path=Config.CNN_PATH,
        transform=cnn_transform,
        classes=Config.CNN_CLASSES, 
        #device=Config.DEVICE
    )

    # 5. Traffic Engine (Dùng biến s_id đã tự động nhận diện)
    engine = TrafficLogic(
        yolo_ai=ai_yolo, 
        cnn_service=cnn_service, 
        pre_proc=pre_proc, 
        uart=uart, 
        cam=cam,
        eth_service=eth_service,
        station_id=s_id, # Truyền s_id vào đây
    )
    engine.auto_mode = True          
    engine.INTERVAL_RUN = 10         
    engine.INTERVAL_RUN1 = 60        
    # Đăng ký callback cho UART
    uart.start_listening(engine.uart_esp32_rasp)

    return engine, cam, Config, ROI_lane