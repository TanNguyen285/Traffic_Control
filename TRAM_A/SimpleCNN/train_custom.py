import os
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
from model.dataset_custom import get_data_loaders
from model.custom import SimpleCNN

def create_run_dir(base_dir='runs'):
    """Tự động tạo thư mục runs/exp1, runs/exp2... giống YOLO"""
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    exp_num = 1
    while True:
        run_dir = os.path.join(base_dir, f'exp{exp_num}')
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
            print(f"[*] Đã tạo thư mục lưu kết quả: {run_dir}")
            return run_dir
        exp_num += 1

def plot_and_save_results(train_losses, val_losses, val_accuracies, all_preds, all_labels, class_names, save_dir):
    """Vẽ biểu đồ và lưu vào thư mục save_dir"""
    # 1. Vẽ biểu đồ Loss và Accuracy
    epochs = range(1, len(train_losses) + 1)
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, label='Train Loss')
    plt.plot(epochs, val_losses, label='Val Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.plot(epochs, val_accuracies, label='Val Accuracy', color='green')
    plt.title('Validation Accuracy')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy (%)')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_results.png'))
    plt.close()

    # 2. Vẽ Confusion Matrix
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix')
    plt.xlabel('Dự đoán (Predicted)')
    plt.ylabel('Thực tế (True)')
    plt.savefig(os.path.join(save_dir, 'confusion_matrix.png'))
    plt.close()

    # 3. In Classification Report
    report = classification_report(all_labels, all_preds, target_names=class_names, zero_division=0)
    with open(os.path.join(save_dir, 'classification_report.txt'), 'w') as f:
        f.write(report)

def train_model():
    # --- CẤU HÌNH ---
    DATA_DIR = './dataset'
    BATCH_SIZE = 16        
    IMG_SIZE = 224          
    EPOCHS = 20             
    LEARNING_RATE = 0.002   
    WEIGHT_DECAY = 1.09e-6  
    MOMENTUM = 0.987        
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Đang sử dụng thiết bị tính toán: {DEVICE}")

    # Tạo thư mục lưu kết quả (runs/exp...)
    SAVE_DIR = create_run_dir()

    train_loader, val_loader, class_to_idx = get_data_loaders(DATA_DIR, batch_size=BATCH_SIZE, img_size=IMG_SIZE)
    class_names = list(class_to_idx.keys())

    # ==========================================
    # 1. ĐỔI NUM_CLASSES SANG 2
    # ==========================================
    model = SimpleCNN(num_classes=2).to(DEVICE)
    
    # ==========================================
    # 2. ĐỔI HÀM LOSS SANG CROSS_ENTROPY
    # ==========================================
    criterion = nn.CrossEntropyLoss() 
    
    optimizer = optim.SGD(model.parameters(), 
                          lr=LEARNING_RATE, 
                          momentum=MOMENTUM, 
                          weight_decay=WEIGHT_DECAY)
    
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    best_val_acc = 0.0
    history_train_loss, history_val_loss, history_val_acc = [], [], []

    for epoch in range(EPOCHS):
        # --- TRAIN ---
        model.train()
        train_loss = 0.0
        for images, labels in train_loader:
            # ==========================================
            # 3. ÉP KIỂU NHÃN SANG .long() (Số nguyên)
            # ==========================================
            images, labels = images.to(DEVICE), labels.to(DEVICE).long()
            
            optimizer.zero_grad()
            
            # BỎ .squeeze(), model sẽ trả ra tensor kích thước [batch_size, 2]
            outputs = model(images) 
            
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * images.size(0)
        
        train_loss = train_loss / len(train_loader.dataset)
        history_train_loss.append(train_loss)

        # --- VALIDATION ---
        model.eval()
        val_loss = 0.0
        corrects = 0
        current_preds, current_labels = [], []

        with torch.no_grad():
            for images, labels in val_loader:
                # ÉP KIỂU NHÃN SANG .long()
                images, labels = images.to(DEVICE), labels.to(DEVICE).long()
                
                # BỎ .squeeze()
                outputs = model(images)
                
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                
                # ==========================================
                # 4. ĐỔI THUẬT TOÁN DỰ ĐOÁN SANG ARGMAX
                # ==========================================
                # Tìm class có điểm số cao nhất trong 2 class xuất ra
                preds = torch.argmax(outputs, dim=1)
                
                corrects += torch.sum(preds == labels).item()
                
                current_preds.extend(preds.cpu().numpy())
                current_labels.extend(labels.cpu().numpy())

        val_loss = val_loss / len(val_loader.dataset)
        val_acc = corrects / len(val_loader.dataset)
        
        history_val_loss.append(val_loss)
        history_val_acc.append(val_acc * 100)
        
        # Scheduler cập nhật LR MỖI EPOCH
        scheduler.step()
        
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1:02d}/{EPOCHS} | LR: {current_lr:.6f} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.2f}%")

        # Lưu model nếu tốt hơn
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            model_path = os.path.join(SAVE_DIR, 'best_cnn_model.pth')
            torch.save(model.state_dict(), model_path)
            print(f"  -> Đã lưu mô hình mới tốt nhất (Acc: {best_val_acc*100:.2f}%)!")

        # Cập nhật biểu đồ sau mỗi epoch
        plot_and_save_results(
            history_train_loss, 
            history_val_loss, 
            history_val_acc, 
            current_preds, 
            current_labels, 
            class_names, 
            SAVE_DIR
        )

    print(f"\n[*] Hoàn thành toàn bộ quá trình huấn luyện! Kết quả lưu tại: {SAVE_DIR}")

if __name__ == "__main__":
    train_model()