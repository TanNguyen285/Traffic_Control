import torch
import torch.nn as nn

class GLKA(nn.Module):
    def __init__(self, dim):
        super().__init__()
        # 1. Local Focus (DW 5x5)
        self.conv0 = nn.Conv2d(dim, dim, 5, padding=2, groups=dim)
        
        # 2. Global Focus (Dilation đa nhánh - học tư duy UniRepLKNet)
        # Nhánh này giúp nhìn xa mà không làm nặng model
       # self.conv_spatial_1 = nn.Conv2d(dim, dim, 7, stride=1, padding=9, groups=dim, dilation=3)
        self.conv_spatial_1 = nn.Conv2d(dim, dim, 7, stride=1, padding=9, groups=dim, dilation=3)
        self.bn1 = nn.BatchNorm2d(dim)

        # Nhánh 2: Medium Kernel (3x3, dil=3) -> Cảm nhận vùng 7x7
        self.conv_spatial_2 = nn.Conv2d(dim, dim, 3, stride=1, padding=3, groups=dim, dilation=3)
        self.bn2 = nn.BatchNorm2d(dim)
        


        # 3. Channel Attention (SE Block) - Giúp AI biết kênh nào quan trọng cho kẹt xe
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(dim, dim // 8, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(dim // 8, dim, 1),
            nn.Sigmoid()
        )
    

    def forward(self, x):
        u = x.clone()
        # Mix thông tin local và global
        attn = self.conv0(x)
        attn = self.conv_spatial_1(attn) + self.conv_spatial_2(attn) 
        
       # attn = self.conv1(attn)
        # Lọc qua SE Block trước khi nhân attention map
        attn = attn * self.se(attn)
        

        return u * attn
    

    
def conv_bn_relu(in_channels, out_channels, kernel_size, stride=1, padding=0, groups=1):
    """Khối Convolution tiêu chuẩn đi kèm BatchNorm và ReLU6"""
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU6(inplace=True)
    )

class EfficientBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride, expansion_ratio=2, use_glka=False):
        super(EfficientBlock, self).__init__()
        self.stride = stride
        self.use_glka = use_glka
        self.use_residual = (stride == 1 and in_channels == out_channels)
        hidden_dim = in_channels * expansion_ratio

        # 1. Mở rộng kênh
        self.expand = conv_bn_relu(in_channels, hidden_dim, kernel_size=1)
        
        # 2. Xử lý không gian (DW 3x3 hoặc GLKA)
        if self.use_glka:
            if self.stride == 2:
                # Nếu giảm ảnh (Stride 2), vẫn cần DW 3x3 để nén ảnh mịn
                self.dw = conv_bn_relu(hidden_dim, hidden_dim, kernel_size=3, stride=2, padding=1, groups=hidden_dim)
                self.glka = GLKA(hidden_dim)
            else:
                # Nếu Stride 1, BỎ HOÀN TOÀN DW 3x3, chỉ dùng GLKA cho nhẹ và bao quát
                self.dw = nn.Identity() 
                self.glka = GLKA(hidden_dim)
        else:
            # Nếu không dùng GLKA, quay lại DW 3x3 truyền thống
            self.dw = conv_bn_relu(hidden_dim, hidden_dim, kernel_size=3, stride=stride, padding=1, groups=hidden_dim)
            self.glka = nn.Identity()

        # 3. Nén kênh
        self.project = nn.Sequential(
            nn.Conv2d(hidden_dim, out_channels, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(out_channels),
        )

    def forward(self, x):
        identity = x
        out = self.expand(x)
        out = self.dw(out)  
        out = self.glka(out) 
        out = self.project(out)
        
        if self.use_residual:
            return identity + out
        return out

class Simple_GLKA(nn.Module):
    def __init__(self, num_classes=2):
        super(Simple_GLKA, self).__init__()
        
        # Layer 1: Lớp cửa ngõ (Conv1)
        self.stem = conv_bn_relu(3, 32, kernel_size=3, stride=2, padding=1)

        # Layers 2 đến 7: Cấu trúc 6 khối phân tầng (Thêm tham số use_lka)
        self.blocks = nn.Sequential(
            # Layer 2: EB1 (Ảnh còn to -> không dùng GLKA)
            EfficientBlock(in_channels=32, out_channels=32, stride=1, expansion_ratio=2, use_glka=False),
            
            # Layer 3: EB2 
            EfficientBlock(in_channels=32, out_channels=64, stride=2, expansion_ratio=2, use_glka=True),
            
            # ==========================================
            # ĐIỂM VÀNG CHO GLKA: EB3 và EB4
            # Tại đây ảnh khoảng 56x56 và 28x28, GLKA bao quát được tổng thể
            # ==========================================
            # Layer 4: EB3 
            EfficientBlock(in_channels=64, out_channels=64, stride=1, expansion_ratio=2, use_glka=True),
            
            # Layer 5: EB4 (Có Stride=2 để giảm ảnh, DW sẽ giảm trước rồi GLKA quét sau)
            EfficientBlock(in_channels=64, out_channels=128, stride=2, expansion_ratio=2, use_glka=True),
            
            # Layer 6: EB5 (Ảnh đã nhỏ, GLKA vẫn có ích để bao quát tổng thể)
            EfficientBlock(in_channels=128, out_channels=128, stride=1, expansion_ratio=2, use_glka=False),
            
            # Layer 7: EB6 
            EfficientBlock(in_channels=128, out_channels=256, stride=2, expansion_ratio=2, use_glka=False),
        )

        # Layer 8 & 9: Pooling và Phân loại
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), # Hoạt động giống GlobalAvgPool
            nn.Flatten(),
            nn.Dropout(p=0.3),       # Chống học vẹt
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.classifier[0](x) # AdaptiveAvgPool2d
        features = torch.flatten(x, 1) # Đây là vector đặc trưng (256 chiều)
        out = self.classifier[1:](features) # Flatten, Dropout, Linear
        return out, features # Trả về cả 2

# ==========================================
# PHẦN KIỂM TRA MÔ HÌNH
# ==========================================
if __name__ == "__main__":
    model = Simple_GLKA(num_classes=2)
    
    # Tính toán tổng số tham số
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Tổng số tham số: {total_params / 1e6:.3f} M")
    
    # Chạy thử với ảnh đầu vào 224x224 (Như bạn yêu cầu)
    test_input = torch.randn(1, 3, 224, 224)
    out, features = model(test_input)
    
    print(f"Kích thước tensor phân loại (Out): {out.shape}") 
    print(f"Kích thước vector đặc trưng (Features): {features.shape}") 
  


