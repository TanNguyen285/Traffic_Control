import requests
import time

# Đã sửa thành port 8000 cho khớp với code app.py của bạn!
WEB_URL = "http://127.0.0.1:8000/api/mock_esp32" 

print("==========================================")
print(" 🚀 ĐIỀU KHIỂN TỪ XA: GIẢ LẬP ESP32 -> WEB")
print("==========================================")
print("Đảm bảo bạn ĐÃ CHẠY app.py bên VSCode nhé!\n")

while True:
    print("-" * 40)
    print("[1] - ESP32 gửi lệnh 'run' (Chạy chu kỳ)")
    print("[2] - ESP32 gửi lệnh 'run1' (Xả trạm m2)")
    print("[q] - Thoát")
    
    lua_chon = input("👉 Bấm phím lựa chọn: ").strip().lower()
    
    if lua_chon == 'q':
        break
        
    signal = ""
    if lua_chon == '1': signal = "run"
    elif lua_chon == '2': signal = "run1"
    else: continue

    print(f"\n📡 Đang bắn tín hiệu [{signal}] vào hệ thống Web (Port 8000)...")
    try:
        response = requests.get(f"{WEB_URL}/{signal}", timeout=10)
        data = response.json()
        
        if data.get("status") == "Lỗi":
            print(f"⚠️ WEB BÁO LỖI: {data.get('message')}")
        else:
            print("✅ [WEB ĐÃ XỬ LÝ VÀ PHẢN HỒI]")
            print(f"   -> Lệnh tạo ra (Gửi xuống UART): {data.get('lenh_tra_ve_uart_cmd')}")
            print(f"   -> Trạng thái trạm mình: {data.get('ket_xe_khong')} (Số xe: {data.get('so_xe_hien_tai')})")
        
    except requests.exceptions.ConnectionError:
        print("❌ LỖI: Không kết nối được. Bạn đã chạy 'python app.py' bên VSCode chưa?")
    except Exception as e:
        print(f"❌ LỖI: {e}")
    print("\n")