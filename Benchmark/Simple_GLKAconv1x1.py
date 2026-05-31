import torch
import torch.nn as nn
import torch.nn.functional as F

class GLKA(nn.Module):
    def __init__(self, dim, out_dim=None, stride=1):
        super().__init__()
        self.dim = dim
        self.out_dim = out_dim if out_dim is not None else dim  # ← thêm out_dim
        self.K = 13
        self.stride = stride

        self.conv0 = nn.Conv2d(dim, dim, 5, stride=stride, padding=2, groups=dim)
        
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(dim, dim // 8, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(dim // 8, dim, 1),
            nn.Sigmoid()
        )

        self.branch1 = nn.Sequential(
            nn.Conv2d(dim, dim, 3, padding=1, groups=dim, dilation=1),
            nn.BatchNorm2d(dim)
        )
        self.branch2 = nn.Sequential(
            nn.Conv2d(dim, dim, 3, padding=3, groups=dim, dilation=3),
            nn.BatchNorm2d(dim)
        )
        self.branch3 = nn.Sequential(
            nn.Conv2d(dim, dim, 5, padding=4, groups=dim, dilation=2),
            nn.BatchNorm2d(dim)
        )
        self.branch4 = nn.Sequential(
            nn.Conv2d(dim, dim, 5, padding=6, groups=dim, dilation=3),
            nn.BatchNorm2d(dim)
        )

        # ← conv_mix thay thế cho conv1x1 bên ngoài, dim → out_dim
        self.conv_mix = nn.Sequential(
            nn.Conv2d(dim, self.out_dim, kernel_size=1, bias=False),
            nn.BatchNorm2d(self.out_dim),
        )

        self.reparam_conv = None

    def forward(self, x):
        global_conv = self.conv0(x)
        anchor = global_conv * self.se(global_conv)
        
        if self.reparam_conv is not None:
            branch_main = self.reparam_conv(global_conv)
        else:
            branch_main = self.branch1(global_conv) + self.branch2(global_conv) + \
                          self.branch3(global_conv) + self.branch4(global_conv)
        
        # ← mix ngay tại đây, bỏ phép nhân raw ra ngoài
        return self.conv_mix(anchor * branch_main)

    def switch_to_deploy(self):
        w1, b1 = self._fuse_bn(self.branch1)
        w2, b2 = self._fuse_bn(self.branch2)
        w3, b3 = self._fuse_bn(self.branch3)
        w4, b4 = self._fuse_bn(self.branch4)

        W_equiv = self._to_target_k(w1, 1) + self._to_target_k(w2, 3) + \
                  self._to_target_k(w3, 2) + self._to_target_k(w4, 3)
        B_equiv = b1 + b2 + b3 + b4
        
        self.reparam_conv = nn.Conv2d(self.dim, self.dim, self.K, padding=self.K//2, groups=self.dim)
        self.reparam_conv.weight.data = W_equiv
        self.reparam_conv.bias.data = B_equiv
        
        del self.branch1, self.branch2, self.branch3, self.branch4

    def _fuse_bn(self, sequential_block):
        conv = sequential_block[0]
        bn = sequential_block[1]
        std = (bn.running_var + bn.eps).sqrt()
        t = (bn.weight / std).reshape(-1, 1, 1, 1)
        fused_weight = conv.weight * t
        fused_bias = bn.bias - bn.running_mean * bn.weight / std
        return fused_weight, fused_bias

    def _to_target_k(self, k, d):
        c, m, orig_k, _ = k.shape
        kd = (orig_k - 1) * d + 1
        sparse = torch.zeros((c, m, kd, kd), device=k.device)
        sparse[:, :, ::d, ::d] = k
        pad = (self.K - kd) // 2
        return F.pad(sparse, [pad, pad, pad, pad])


def conv_bn_relu(in_channels, out_channels, kernel_size, stride=1, padding=0, groups=1):
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

        # 1. Expand
        self.expand = conv_bn_relu(in_channels, hidden_dim, kernel_size=1)
        
        # 2. Spatial Processing
        if self.use_glka:
            # ← GLKA tự mix ra out_channels luôn, không cần project nữa
            self.spatial = GLKA(hidden_dim, out_dim=out_channels, stride=stride)
        else:
            # DW chuẩn + project giữ nguyên
            self.spatial = conv_bn_relu(hidden_dim, hidden_dim, kernel_size=3, stride=stride, padding=1, groups=hidden_dim)
            self.project = nn.Sequential(
                nn.Conv2d(hidden_dim, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels),
            )

    def forward(self, x):
        identity = x
        out = self.expand(x)
        out = self.spatial(out)

        # ← chỉ project khi không dùng GLKA (GLKA đã mix ra out_channels rồi)
        if not self.use_glka:
            out = self.project(out)
        
        if self.use_residual:
            return identity + out
        return out


class Simple_GLKA(nn.Module):
    def __init__(self, num_classes=2):
        super(Simple_GLKA, self).__init__()
        
        self.stem = conv_bn_relu(3, 32, kernel_size=3, stride=2, padding=1)

        self.blocks = nn.Sequential(
            EfficientBlock(32,  32,  stride=1, expansion_ratio=2, use_glka=False),
            EfficientBlock(32,  64,  stride=2, expansion_ratio=2, use_glka=True),
            EfficientBlock(64,  64,  stride=1, expansion_ratio=2, use_glka=True),
            EfficientBlock(64,  128, stride=2, expansion_ratio=2, use_glka=True),
            EfficientBlock(128, 128, stride=1, expansion_ratio=2, use_glka=False),
            EfficientBlock(128, 256, stride=2, expansion_ratio=2, use_glka=False),
        )

        self.classifier_pool = nn.AdaptiveAvgPool2d(1)
        self.classifier_fc = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.3),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.classifier_pool(x)
        features = torch.flatten(x, 1)
        out = self.classifier_fc(features)
        return out, features


if __name__ == "__main__":
    import copy

    model = Simple_GLKA(num_classes=2).eval()
    
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Kiến trúc GLKA Net")
    print(f"Tổng số tham số: {total_params / 1e6:.3f} M")
    
    test_input = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        out, features = model(test_input)
    
    print(f"Input:          {test_input.shape}")
    print(f"Output (Logits):{out.shape}") 
    print(f"Features vector:{features.shape}")

    model_deploy = copy.deepcopy(model)
    for m in model_deploy.modules():
        if isinstance(m, GLKA):
            m.switch_to_deploy()
    with torch.no_grad():
        out_deploy, _ = model_deploy(test_input)
    diff = (out - out_deploy).abs().max().item()
    print(f"Train vs Deploy max diff: {diff:.2e}  {'✓' if diff < 1e-4 else '✗ FAIL'}")