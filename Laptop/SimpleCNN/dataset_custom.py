import os
import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

def get_data_loaders(data_dir, batch_size=16, img_size=224, num_workers=2):
    """
    Hàm chuẩn bị DataLoader cho bài toán nhận diện kẹt xe.
    - img_size: Mặc định 224 (Điểm cân bằng hoàn hảo giữa độ nét và tốc độ cho Pi 5).
    - num_workers: Để 2 hoặc 4 tùy số luồng CPU của bạn.
    """
    
    # 1. Data Augmentation cho tập Train (Huấn luyện mô hình "lì đòn" hơn)
    train_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        # Thêm xoay nhẹ (±5 độ): Giúp mô hình quen với việc camera bị gió thổi rung lắc hoặc lắp lệch
        transforms.RandomRotation(degrees=5), 
        transforms.RandomHorizontalFlip(p=0.5),
        # Tăng nhẹ biên độ Jitter: Giúp mô hình thích nghi tốt hơn với chênh lệch ánh sáng sáng sớm / chập tối
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3), 
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                             std=[0.229, 0.224, 0.225])
    ])

    # 2. Tập Val: Phải giữ nguyên bản chất thực tế, CHỈ Resize và Normalize
    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                             std=[0.229, 0.224, 0.225])
    ])

    # 3. Kiểm tra đường dẫn và đọc dữ liệu
    train_dir = os.path.join(data_dir, 'train')
    val_dir = os.path.join(data_dir, 'val')

    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        raise FileNotFoundError(f"LỖI: Không tìm thấy thư mục 'train' hoặc 'val' bên trong {data_dir}")

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_transforms)

    # 4. Đóng gói vào DataLoader
    # CẢNH BÁO: Nếu chạy trên Windows mà bị lỗi đa luồng (BrokenPipeError), hãy đổi num_workers=0
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, 
                              num_workers=num_workers, pin_memory=True)
    
    # Tập val không cần shuffle (xáo trộn) để dễ debug và theo dõi kết quả
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, 
                            num_workers=num_workers, pin_memory=True)

    # 5. In báo cáo tóm tắt
    print(f"[*] Đã tải xong Dữ liệu Traffic!")
    print(f"    - Số ảnh Train: {len(train_dataset)}")
    print(f"    - Số ảnh Validation: {len(val_dataset)}")
    print(f"    - Danh sách các nhãn (Classes): {train_dataset.class_to_idx}")
    
    return train_loader, val_loader, train_dataset.class_to_idx

# ==========================================
# CÁCH SỬ DỤNG
# ==========================================
if __name__ == "__main__":
    # Thay 'path/to/your/dataset' bằng đường dẫn thực tế của bạn
    # Ví dụ: data_dir = './traffic_dataset'
    data_dir = './dataset' 
    
    try:
        train_loader, val_loader, class_map = get_data_loaders(data_dir, batch_size=16, img_size=224)
        
        # Lấy thử 1 batch ra xem
        images, labels = next(iter(train_loader))
        print(f"\n[*] Kích thước 1 batch ảnh: {images.shape}") # Sẽ ra [16, 3, 224, 224]
        print(f"[*] Kích thước 1 batch nhãn: {labels.shape}") # Sẽ ra [16]
        
    except FileNotFoundError as e:
        print(e)