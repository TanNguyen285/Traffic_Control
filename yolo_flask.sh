import cv2

# Mở camera (0 là camera mặc định)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Không thể mở camera")
    exit()

while True:
    # Đọc khung hình từ camera
    ret, frame = cap.read()
    
    if not ret:
        print("Không thể nhận khung hình")
        break

    # Hiển thị khung hình
    cv2.imshow('Camera Test', frame)

    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng camera và đóng cửa sổ
cap.release()
cv2.destroyAllWindows()
