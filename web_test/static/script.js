// DOM Elements
const originalImg = document.getElementById("anhgoc");
const processedImg = document.getElementById("sauxuly");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");

// UI Functions
function uiStart() {
    loading.style.display = "block";
    cameraCaptureBtn.disabled = true;
    cameraCaptureBtn.style.opacity = "0.7";
}

function uiEnd() {
    loading.style.display = "none";
    cameraCaptureBtn.disabled = false;
    cameraCaptureBtn.style.opacity = "1";
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

// Update Functions
function updateDensity(count) {
    const total = document.getElementById("tongxe");
    const level = document.getElementById("mode");
    if (!total || !level) return;

    total.textContent = count;
    if (count < 5) level.textContent = "🟢 Ít";
    else if (count <= 10) level.textContent = "🟡 Trung bình";
    else if (count <= 15) level.textContent = "🟠 Khá";
    else level.textContent = "🔴 Đông";
}

function time_light(g, y, r) {
    const gt = document.getElementById("greenTime");
    const yt = document.getElementById("yellowTime");
    const rt = document.getElementById("redTime");
    
    if(gt) gt.textContent = `${g}s`;
    if(yt) yt.textContent = `${y}s`;
    if(rt) rt.textContent = `${r}s`;
}

// Logic xử lý dữ liệu trả về từ API
function xulyKetQua(data) {
    // 1. Cập nhật số lượng từng loại xe
    if (Array.isArray(data.counts)) {
        let totalCount = 0;
        data.counts.forEach((c, i) => {
            const el = document.getElementById(`count-${i}`);
            if (el) el.textContent = c;
            totalCount += c;
        });
        updateDensity(totalCount);
    }

    // 2. Hiển thị ảnh gốc đã chụp
    if (data.input_image) {
        originalImg.src = data.input_image;
        originalImg.classList.add("active");
    }

    // 3. Hiển thị ảnh đã qua YOLO xử lý
    if (data.yolo_image) {
        processedImg.src = data.yolo_image;
        processedImg.classList.add("active");
    }

    // 4. Cập nhật thời gian đèn
    const yellow = data.yellow_seconds ?? 3;
    const red = data.total_seconds ?? data.red_seconds ?? 0;
    const green = data.green_seconds ?? Math.max(0, red - yellow);
    time_light(green, yellow, red);
    
    showError("");
}

// Gọi API Capture
async function chupVaPhanTich() {
    uiStart();
    showError("");
    try {
        const res = await fetch(`/camera_capture`, { method: "POST" });
        if (!res.ok) throw new Error("Lỗi kết nối server.");
        
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        
        xulyKetQua(data);
    } catch (err) {
        showError(err.message);
    } finally {
        uiEnd();
    }
}

// Event Listeners
cameraCaptureBtn.addEventListener("click", chupVaPhanTich);

// Tự động kiểm tra trạng thái camera khi trang load (nếu cần)
window.addEventListener("DOMContentLoaded", () => {
    console.log("Hệ thống YOLOv26 đã sẵn sàng.");
});