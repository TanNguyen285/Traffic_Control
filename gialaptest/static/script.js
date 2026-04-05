// Frontend Script for YOLO Detection - Hardware Trigger Version

// DOM Elements
const form = document.getElementById("yoloForm");
const originalImg = document.getElementById("anhgoc");
const processedImg = document.getElementById("sauxuly");
const cameraPreview = document.getElementById("cameraPreview");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");

// --- UI Functions ---
function uiStart() {
    loading.style.display = "block";
    // Kiểm tra tồn tại trước khi disable để tránh lỗi crash
    if (cameraCaptureBtn) cameraCaptureBtn.disabled = true;
}

function uiEnd() {
    loading.style.display = "none";
    if (cameraCaptureBtn) cameraCaptureBtn.disabled = false;
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

// --- Update Functions ---
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
    if (gt) gt.textContent = `${g}s`;
    if (yt) yt.textContent = `${y}s`;
    if (rt) rt.textContent = `${r}s`;
}

// --- Core Processing ---
function xulyanhchupman(data) {
    if (!data || Object.keys(data).length === 0) return;

    let totalCount = 0;
    if (Array.isArray(data.counts)) {
        data.counts.forEach((c, i) => {
            const el = document.getElementById(`count-${i}`);
            if (el) el.textContent = c;
            totalCount += c;
        });
    }
    updateDensity(totalCount);

    if (data.input_image) {
        originalImg.src = data.input_image;
        originalImg.classList.add("active");
    }

    if (data.yolo_image) {
        processedImg.onload = () => processedImg.classList.add("active");
        processedImg.src = data.yolo_image;
    }

    const yellow = data.yellow_seconds ?? 3;
    const total = data.total_seconds ?? data.red_seconds ?? 0;
    const green = data.green_seconds ?? Math.max(0, total - yellow);
    time_light(green, yellow, total);
    showError("");
}

// --- API Calls ---

// 1. Chụp thủ công từ Camera
async function chupmanhinh() {
    uiStart();
    showError("");
    try {
        // ĐÃ GỠ uploadfile() vì không dùng ảnh từ máy tính nữa
        const res = await fetch(`/camera_capture`, { method: "POST" });
        if (!res.ok) throw new Error("Lỗi server: " + res.status);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        xulyanhchupman(data);
    } catch (err) {
        showError("Lỗi: " + err.message);
    } finally {
        uiEnd();
    }
}

// 2. HÀM QUAN TRỌNG: Tự động nhảy ảnh khi có biến đổi (Long Polling)
async function autoListen() {
    try {
        const response = await fetch('/update_web');
        if (response.status === 200) {
            const data = await response.json();
            console.log("Hệ thống phát hiện biến đổi, tự cập nhật ảnh...");
            xulyanhchupman(data);
        }
    } catch (e) {
        console.log("Mất kết nối server, đang thử lại...");
    }
    setTimeout(autoListen, 500); 
}

// --- Khởi tạo ---
window.addEventListener("DOMContentLoaded", () => {
    cameraPreview.src = "/camera_stream";
    autoListen(); // Bật tính năng hóng biến đổi
});

if (cameraCaptureBtn) {
    cameraCaptureBtn.addEventListener("click", (e) => {
        e.preventDefault();
        chupmanhinh();
    });
}

if (form) {
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        chupmanhinh();
    });
}