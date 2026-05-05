import torch
import torch.nn as nn

import torch
import torch.nn as nn

class EnhancedLKA(nn.Module):
    def __init__(self, dim):
        super().__init__()
        # 1. Local Focus (DW 5x5)
        self.conv0 = nn.Conv2d(dim, dim, 5, padding=2, groups=dim)
        
        # 2. Global Focus (Dilation đa nhánh)
        # Nhánh 1: k7, d2 -> padding = (7-1)*2 // 2 = 6
        self.conv_spatial_1 = nn.Conv2d(dim, dim, 7, stride=1, padding=6, groups=dim, dilation=2)
        # Nhánh 2: k5, d3 -> padding = (5-1)*3 // 2 = 6
        self.conv_spatial_2 = nn.Conv2d(dim, dim, 5, stride=1, padding=6, groups=dim, dilation=3) 
        
        # 3. Channel Attention (SE Block)
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(dim, dim // 8, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(dim // 8, dim, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        u = x.clone() # Giữ lại đầu vào gốc để làm identity
        
        # Step 1: Trích xuất đặc trưng Local
        local_feat = self.conv0(x)
        
        # Step 2: Tính Channel Attention (SE) dựa trên local_feat
        # Sau đó áp dụng SE lên chính local_feat để tạo base_se
        base_se = local_feat * self.se(local_feat)
        
        # Step 3: Global Focus (Dilation đa nhánh)
        # Lấy thông tin từ base_se để quét không gian rộng hơn
        attn = self.conv_spatial_1(local_feat) + self.conv_spatial_2(local_feat)
        
        # Step 4: [QUAN TRỌNG] Nhân attention map cuối cùng với đầu vào gốc u
        # attn đóng vai trò là bộ lọc (mask), u là dữ liệu ảnh
        return base_se* attn

def conv_bn_relu(in_channels, out_channels, kernel_size, stride=1, padding=0, groups=1):
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, groups=groups, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU6(inplace=True)
    )

class EfficientBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride, expansion_ratio=2, use_lka=False):
        super(EfficientBlock, self).__init__()
        self.stride = stride
        self.use_lka = use_lka
        self.use_residual = (stride == 1 and in_channels == out_channels)
        hidden_dim = in_channels * expansion_ratio

        self.expand = conv_bn_relu(in_channels, hidden_dim, kernel_size=1)
        
        if self.use_lka:
            if self.stride == 2:
                self.dw = conv_bn_relu(hidden_dim, hidden_dim, kernel_size=3, stride=2, padding=1, groups=hidden_dim)
                self.lka = EnhancedLKA(hidden_dim)
            else:
                self.dw = nn.Identity() 
                self.lka = EnhancedLKA(hidden_dim)
        else:
            self.dw = conv_bn_relu(hidden_dim, hidden_dim, kernel_size=3, stride=stride, padding=1, groups=hidden_dim)
            self.lka = nn.Identity()

        self.project = nn.Sequential(
            nn.Conv2d(hidden_dim, out_channels, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(out_channels),
        )

    def forward(self, x):
        identity = x
        out = self.expand(x)
        out = self.dw(out)
        out = self.lka(out)
        out = self.project(out)
        
        if self.use_residual:
            return identity + out
        return out

class Simple_GLKA(nn.Module):
    def __init__(self, num_classes=2):
        super(Simple_GLKA, self).__init__()
        
        self.stem = conv_bn_relu(3, 32, kernel_size=3, stride=2, padding=1)

        self.blocks = nn.Sequential(
            # Đã đổi use_glka thành use_lka để khớp với EfficientBlock
            EfficientBlock(32, 32, stride=1, expansion_ratio=2, use_lka=False),
            EfficientBlock(32, 64, stride=2, expansion_ratio=2, use_lka=False),
            EfficientBlock(64, 64, stride=1, expansion_ratio=2, use_lka=True),
            EfficientBlock(64, 128, stride=2, expansion_ratio=2, use_lka=True),
            EfficientBlock(128, 128, stride=1, expansion_ratio=2, use_lka=False),
            EfficientBlock(128, 256, stride=2, expansion_ratio=2, use_lka=False),
        )

        self.avgpool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        
        x = self.avgpool(x)
        features = torch.flatten(x, 1) 
        out = self.classifier(features)
        return out, features

if __name__ == "__main__":
    model = Simple_GLKA(num_classes=2)
    test_input = torch.randn(1, 3, 224, 224)
    out, features = model(test_input)
    
    print(f"Tổng tham số: {sum(p.numel() for p in model.parameters())/1e6:.3f} M")
    print(f"Out shape: {out.shape}") 
    print(f"Features shape: {features.shape}")