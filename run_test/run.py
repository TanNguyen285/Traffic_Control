import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from ultralytics import YOLO
from PIL import Image, ImageTk, ImageDraw
import csv
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================
# Load YOLO model path
# =============================
model_path = os.path.join(BASE_DIR, "../../runs/detect/my_yolov8n_train_meme/weights/best.pt")

if not os.path.exists(model_path):
    model_path = "runs/detect/my_yolov8n_train_meme/weights/best.pt"
# =============================


# =============================
# ROI controller state
# =============================
ROI = {"x1": None, "y1": None, "x2": None, "y2": None}
drawing = False
loaded_preview_path = None


# -----------------------------
# VẼ ROI LÊN ẢNH PREVIEW
# -----------------------------
def draw_roi_on_preview(preview_img):
    if ROI["x1"] is None:
        return preview_img

    img = preview_img.copy()
    draw = ImageDraw.Draw(img)

    draw.rectangle(
        [ROI["x1"], ROI["y1"], ROI["x2"], ROI["y2"]],
        outline="red",
        width=3
    )

    return img


# -----------------------------
# HIỂN THỊ ẢNH LÊN GUI
# -----------------------------
def show_image(img_path, img_label):
    global loaded_preview_path
    loaded_preview_path = img_path

    img = Image.open(img_path)
    img = img.resize((500, 400))
    img = draw_roi_on_preview(img)

    img_tk = ImageTk.PhotoImage(img)
    img_label.configure(image=img_tk)
    img_label.image = img_tk


# -----------------------------
# CROP ROI
# -----------------------------
def crop_roi(image_path):
    img = Image.open(image_path)
    w, h = img.size

    # scale lại ROI theo kích thước ảnh gốc
    scale_x = w / 500
    scale_y = h / 400

    x1 = int(min(ROI["x1"], ROI["x2"]) * scale_x)
    y1 = int(min(ROI["y1"], ROI["y2"]) * scale_y)
    x2 = int(max(ROI["x1"], ROI["x2"]) * scale_x)
    y2 = int(max(ROI["y1"], ROI["y2"]) * scale_y)

    cropped = img.crop((x1, y1, x2, y2))

    # tạo file mới an toàn bằng os.path.splitext
    base, ext = os.path.splitext(image_path)
    new_path = f"{base}_roi{ext}"

    cropped.save(new_path)

    return new_path
# -----------------------------
# CHẠY YOLO DETECT TRONG ROI
# -----------------------------
def run_detection(folder, log_widget, img_label):
    try:
        log_widget.insert(tk.END, "🔍 Loading YOLO model...\n")
        log_widget.see(tk.END)

        model = YOLO(model_path)
        CLASS_NAMES = model.names

        img_list = glob.glob(os.path.join(folder, "*.jpg")) + \
                   glob.glob(os.path.join(folder, "*.jpeg")) + \
                   glob.glob(os.path.join(folder, "*.png"))

        os.makedirs("runs/detect/roi_predict", exist_ok=True)

        for img_path in img_list:
            log_widget.insert(tk.END, f"🟦 ROI detect: {os.path.basename(img_path)}\n")
            log_widget.see(tk.END)

            roi_img_path = crop_roi(img_path)

            model.predict(
                source=roi_img_path,
                save=True,
                save_txt=True,
                save_conf=True,
                project="run_test",
                name="roi_predict",
                exist_ok=True
            )

        # Hiển thị ảnh detect cuối
        out_imgs = glob.glob("run_test/detect/roi_predict/*.jpg")
        if out_imgs:
            show_image(out_imgs[-1], img_label)
        log_widget.insert(tk.END, "\n✅ Hoàn thành detect trong ROI!\n")
    except Exception as e:
        log_widget.insert(tk.END, f"\n❌ ERROR: {str(e)}\n")
        messagebox.showerror("Lỗi", str(e))


def start_detection(folder_entry, log_widget, img_label):
    if ROI["x1"] is None:
        messagebox.showerror("Lỗi", "Bạn chưa vẽ ROI!")
        return

    folder = folder_entry.get()
    if not os.path.isdir(folder):
        messagebox.showerror("Lỗi", "Thư mục ảnh không hợp lệ!")
        return

    threading.Thread(target=run_detection, args=(folder, log_widget, img_label)).start()


# -----------------------------
# ROI EVENTS (chuột)
# -----------------------------
def start_draw(event, canvas):
    global drawing
    drawing = True
    ROI["x1"], ROI["y1"] = event.x, event.y


def draw(event, canvas, img_label):
    if not drawing:
        return

    ROI["x2"], ROI["y2"] = event.x, event.y

    show_image(loaded_preview_path, img_label)


def stop_draw(event, canvas):
    global drawing
    drawing = False


# -----------------------------
# GUI
# -----------------------------
def main():
    root = tk.Tk()
    root.title("YOLOv8 ROI Detector")
    root.geometry("1000x520")

    # Chọn folder
    tk.Label(root, text="Folder ảnh cần detect:", font=("Arial", 12)).pack(pady=5)
    frame_folder = tk.Frame(root)
    frame_folder.pack()

    folder_entry = tk.Entry(frame_folder, width=50)
    folder_entry.pack(side=tk.LEFT, padx=5)

    tk.Button(frame_folder, text="Chọn folder",
              command=lambda: folder_entry.insert(0, filedialog.askdirectory())
              ).pack(side=tk.LEFT)

    # Load preview ảnh đầu tiên
    def load_preview():
        folder = folder_entry.get()
        imgs = glob.glob(folder + "/*.jpg") + glob.glob(folder + "/*.png")
        if imgs:
            show_image(imgs[0], img_label)
        else:
            messagebox.showerror("Lỗi", "Không có ảnh trong thư mục!")

    tk.Button(root, text="📸 Load ảnh preview", command=load_preview).pack(pady=5)

    # Khu vực log + ảnh
    frame_main = tk.Frame(root)
    frame_main.pack()

    log_area = scrolledtext.ScrolledText(frame_main, width=55, height=22)
    log_area.pack(side=tk.LEFT, padx=10)

    img_label = tk.Label(frame_main)
    img_label.pack(side=tk.RIGHT, padx=10)

    # ROI events
    img_label.bind("<Button-1>", lambda e: start_draw(e, img_label))
    img_label.bind("<B1-Motion>", lambda e: draw(e, img_label, img_label))
    img_label.bind("<ButtonRelease-1>", lambda e: stop_draw(e, img_label))

    # Run detect
    tk.Button(root, text="🚀 Detect trong ROI",
              font=("Arial", 12, "bold"),
              command=lambda: start_detection(folder_entry, log_area, img_label)
              ).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
