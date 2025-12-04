#!/bin/bash
#dòng đầu là buộc phải có để chỉ định trình thông dịch bash

# Tạo môi trường ảo và cài đặt các phụ thuộc (chỉ cần chạy lần đầu)
# python3 -m venv /path/to/your/name_sh
# source /path/to/your/name_sh/bin/activate
# --- ĐƯỜNG DẪN CẦN CHỈNH SỬA ---
# Thay đường dẫn bên dưới bằng venv thực tế của bạn
VENV_PATH="/path/to/your/name_sh/bin/activate"
APP_PATH="/path/to/your/app/app.py" 


# Kích hoạt môi trường ảo
source "$VENV_PATH"


# Thiết lập biến môi trường của Flask
export FLASK_APP="$APP_PATH"
export FLASK_ENV=production
export PYTHONUNBUFFERED=1


# Chạy Flask server
flask run --host=0.0.0.0 --port=5000