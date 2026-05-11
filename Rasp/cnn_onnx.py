import numpy as np
import onnxruntime as ort
import cv2
from PIL import Image

class Simple_CNN_config:
    def __init__(self, model_path, transform, classes):
        # 1. Khởi tạo ONNX Session (Thay thế cho load model PyTorch)
        # Tự động chọn CUDA nếu có, nếu không thì dùng CPU (mặc định cho Pi 5)
        providers = ['CPUExecutionProvider']
        
        try:
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
        except Exception as e:
            print(f"[!] Lỗi load ONNX: {e}")
            self.session = None

        self.transform = transform
        self.classes = classes

    def predict(self, frame_cv2):
        if self.session is None: 
            return "N/A", 0.0, 0
        
        # 2. Tiền xử lý: Dùng transform của Torch nhưng xuất ra Numpy
        rgb = cv2.cvtColor(frame_cv2, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        
        # Chuyển qua transform để Normalize -> sang Numpy để ONNX hiểu
        input_tensor = self.transform(pil_img).unsqueeze(0).numpy()
        
        # 3. Chạy Inference bằng ONNX Runtime
        outputs = self.session.run(None, {self.input_name: input_tensor})
        logits = outputs[0]

        # 4. Tính Softmax bằng Numpy (Vì không dùng torch.nn.functional)
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        
        # Lấy kết quả
        idx = np.argmax(probs)
        conf = probs[0][idx] * 100
            
        return self.classes[idx], conf, idx

    def draw_prediction(self, frame, label, conf):
        """ Giữ nguyên logic vẽ, chỉ đổi text hiển thị cho rõ là ONNX """
        color = (0, 0, 255) if label == "Ket Xe" else (0, 255, 0)
        
        # Đổi chữ CNN thành CNN-ONNX để bạn dễ theo dõi lúc chạy
        text = f"CNN-ONNX: {label} ({conf:.1f}%)"
        
        cv2.rectangle(frame, (10, 20), (450, 60), (0, 0, 0), -1)
        cv2.putText(frame, text, (20, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        return frame