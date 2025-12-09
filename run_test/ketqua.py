import pandas as pd

csv_path = "runs/detect/my_yolov8n_train_meme/results.csv"

# Đọc file CSV
df = pd.read_csv(csv_path)

# Lấy dòng cuối (epoch cuối)
last = df.iloc[-1]

precision = last["metrics/precision(B)"]
recall = last["metrics/recall(B)"]
map50 = last["metrics/mAP50(B)"]
map5095 = last["metrics/mAP50-95(B)"]

# Tính F1-score
f1 = 2 * (precision * recall) / (precision + recall)

print("\n===== KẾT QUẢ TỔNG HỢP =====")
print(f"Precision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1-score  : {f1:.4f}")
print(f"mAP50     : {map50:.4f}")
print(f"mAP50-95  : {map5095:.4f}")
print("============================\n")
