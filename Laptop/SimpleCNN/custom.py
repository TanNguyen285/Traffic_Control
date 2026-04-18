import torch
import torch.nn as nn

def conv_bn_relu(in_channels, out_channels, kernel_size, stride=1, padding=0, groups=1):
    """Khối Convolution tiêu chuẩn đi kèm BatchNorm và ReLU6"""
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU6(inplace=True)
    )

class EfficientBlock(nn.Module):
    """Khối Inverted Residual Block chuẩn"""
    def __init__(self, in_channels, out_channels, stride, expansion_ratio=2):
        super(EfficientBlock, self).__init__()
        # Kích hoạt Residual NẾU stride = 1 VÀ số kênh đầu vào = đầu ra
        self.use_residual = (stride == 1 and in_channels == out_channels)
        hidden_dim = in_channels * expansion_ratio

        self.conv = nn.Sequential(
            # 1. Pointwise expansion (Mở rộng số kênh)
            conv_bn_relu(in_channels, hidden_dim, kernel_size=1),
            # 2. Depthwise convolution (Tích chập chiều sâu)
            conv_bn_relu(hidden_dim, hidden_dim, kernel_size=3, stride=stride, padding=1, groups=hidden_dim),
            # 3. Pointwise linear projection (Nén lại, KHÔNG dùng ReLU)
            nn.Conv2d(hidden_dim, out_channels, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(out_channels),
        )

    def forward(self, x):
        if self.use_residual:
            return x + self.conv(x) # Cộng kết nối tắt (Residual)
        else:
            return self.conv(x)

class SimpleCNN(nn.Module):
    def __init__(self, num_classes=2):
        super(SimpleCNN, self).__init__()
        
        # Layer 1: Lớp cửa ngõ (Conv1)
        self.stem = conv_bn_relu(3, 32, kernel_size=3, stride=2, padding=1)

        # Layers 2 đến 7: Cấu trúc 6 khối phân tầng xen kẽ Stride 1 và 2
        self.blocks = nn.Sequential(
            # Layer 2: EB1 (Stride 1 -> Kích hoạt Residual)
            EfficientBlock(in_channels=32, out_channels=32, stride=1, expansion_ratio=2),
            
            # Layer 3: EB2 (Stride 2 -> Giảm kích thước ảnh)
            EfficientBlock(in_channels=32, out_channels=64, stride=2, expansion_ratio=2),
            
            # Layer 4: EB3 (Stride 1 -> Kích hoạt Residual)
            EfficientBlock(in_channels=64, out_channels=64, stride=1, expansion_ratio=2),
            
            # Layer 5: EB4 (Stride 2 -> Giảm kích thước ảnh)
            EfficientBlock(in_channels=64, out_channels=128, stride=2, expansion_ratio=2),
            
            # Layer 6: EB5 (Stride 1 -> Kích hoạt Residual)
            EfficientBlock(in_channels=128, out_channels=128, stride=1, expansion_ratio=2),
            
            # Layer 7: EB6 (Stride 2 -> Giảm kích thước ảnh cuối cùng)
            EfficientBlock(in_channels=128, out_channels=256, stride=2, expansion_ratio=2),
        )

        # Layer 8 & 9: Pooling và Phân loại
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), # Hoạt động giống GlobalAvgPool, nhận mọi kích thước ảnh
            nn.Flatten(),
            nn.Dropout(p=0.5),       # Chống học vẹt
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.classifier(x)
        return x

# ==========================================
# PHẦN KIỂM TRA MÔ HÌNH
# ==========================================
if __name__ == "__main__":
    model = SimpleCNN(num_classes=2)
    
    # Tính toán tổng số tham số
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Tổng số tham số: {total_params / 1e6:.3f} M")
    
    # Chạy thử với ảnh đầu vào 160x160 (kích thước tối ưu cho mô hình nhẹ)
    test_input = torch.randn(1, 3, 160, 160)
    output = model(test_input)
    
    print(f"Kích thước tensor đầu ra: {output.shape}") 
    print("Mô hình đã chạy thành công!")