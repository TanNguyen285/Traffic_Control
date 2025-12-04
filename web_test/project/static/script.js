
// ==========================================
// DOM Elements
// ==========================================
const form = document.getElementById("yoloForm");
const imageInput = document.getElementById("imageInput");
const fileNameDisplay = document.getElementById("fileName");

const confSlider = document.getElementById("confSlider");
const iouSlider = document.getElementById("iouSlider");
const confVal = document.getElementById("confVal");
const iouVal = document.getElementById("iouVal");

const originalImg = document.getElementById("originalImg");
const processedImg = document.getElementById("processedImg");
const cameraPreview = document.getElementById("cameraPreview");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");

const downloadBtn = document.getElementById("downloadBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");

const timeDisplay = document.getElementById("timeDisplay");

// ==========================================
// UI Utility Functions_bộ chuyển thòii gian & trạng thái
// ==========================================
let timerInterval = null;
let startTime = null;

function startTimer() {
    startTime = Date.now();
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        if (!timeDisplay) return;
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
        const s = String(elapsed % 60).padStart(2, "0");
        timeDisplay.textContent = `${h}:${m}:${s}`;
    }, 100);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
    if (timeDisplay) timeDisplay.textContent = "00:00:00";
}

function uiStart() {
    loading.style.display = "block";
    if (form.querySelector(".btn-primary")) form.querySelector(".btn-primary").disabled = true;
    startTimer();
}

function uiEnd() {
    loading.style.display = "none";
    if (form.querySelector(".btn-primary")) form.querySelector(".btn-primary").disabled = false;
    stopTimer();
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

function noCache(url) {
    return url + "?t=" + Date.now();
}
// ==========================================
// 1_Tạo FormData để upload
// ==========================================
function createUploadForm(key, value, filename = null) {
    const fd = new FormData();
    if (filename) {
        fd.append(key, value, filename);
    } else {
        fd.append(key, value);
    }
    fd.append("conf", confSlider.value);
    fd.append("iou", iouSlider.value);
    return fd;
}

// ==========================================
// Mật độ xe và Cập nhật thòi gian đèn xanh đỏ vàng
// ==========================================
function updateDensity(count) {
    const total = document.getElementById("totalVehicles");
    const level = document.getElementById("densityLevel");

    if (total) total.textContent = count;
    if (level) {
        if (count < 5) level.textContent = "🟢 Ít";
        else if (count <= 10) level.textContent = "🟡 Trung bình";
        else if (count <= 15) level.textContent = "🟠 Khá";
        else level.textContent = "🔴 Đông";
    }
}

function updateLightTimes(g, y, r) {
    const elG = document.getElementById("greenTime");
    const elY = document.getElementById("yellowTime");
    const elR = document.getElementById("redTime");

    if (elG) elG.textContent = `${g}s`;
    if (elY) elY.textContent = `${y}s`;
    if (elR) elR.textContent = `${r}s`;
}

function showProcessedImage(url) {
    if (processedImg) {
        processedImg.onload = () => processedImg.classList.add("active");
        processedImg.src = url;
    }
}

function handleUploadResponse(data) {
    // Cập nhật số lượng cho mỗi lớp
    let total = 0;
    if (Array.isArray(data.counts)) {
        data.counts.forEach((c, i) => {
            const el = document.getElementById(`count-${i}`);
            if (el) {
                el.textContent = c;
                total += c;
            }
        });
    }
    updateDensity(total);

    // Link for download ảnh đã xử lý
    if (data.processed_image_url && downloadBtn) {
        downloadBtn.href = data.processed_image_url;
    }

    // Thời gian đèn giao thông
    if (typeof data.red_seconds === "number") {
        const r = Number(data.red_seconds);
        const y = Number(data.yellow_seconds || 3);
        const g = Number(data.green_seconds || Math.max(0, r - y));
        updateLightTimes(g, y, r);
    }
}
// ==========================================
// 2_Upload API _  Xử lý Phản hồi_API của ảnh đã tải lên ( lấy từ formData trên)
// ==========================================
async function sendToUpload(formData) {
    uiStart();

    try {
        const res = await fetch("/upload", { method: "POST", body: formData });
        if (!res.ok) throw new Error("Server error: " + res.status);

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        showProcessedImage(noCache(data.processed_image_url));
        handleUploadResponse(data);
        showError("");

    } catch (err) {
        console.error(err);
        showError("Lỗi: " + err.message);
    } finally {
        uiEnd();
    }
}

// ==========================================
// Camera Module_ Capture & Stream
// ==========================================
function startCamera() {
    if (cameraPreview) {
        cameraPreview.src = "/camera_stream";
    }
}

async function captureFrameAndSend() {
    try {
        const res = await fetch("/camera_capture", { method: "POST" });
        if (!res.ok) throw new Error("Capture failed: " + res.status);

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        const imgUrl = noCache(data.image_url);
        if (originalImg) {
            originalImg.src = imgUrl;
            originalImg.classList.add("active");
        }

        // Auto-upload the captured image
        await sendToUpload(createUploadForm("image_url", data.image_url));

    } catch (err) {
        console.error(err);
        showError("Camera: " + err.message);
    }
}

// ==========================================
// EVENT HANDLERS
// ==========================================

// Initialize camera on DOM ready
window.addEventListener("DOMContentLoaded", () => {
    try { startCamera(); } catch (e) { console.error("Camera init failed:", e); }
});

if (cameraCaptureBtn) {
    cameraCaptureBtn.addEventListener("click", captureFrameAndSend);
}

// Hiển thị tên file khi chọn ảnh
if (imageInput) {
    imageInput.addEventListener("change", () => {
        const f = imageInput.files[0];
        if (!f) {
            if (fileNameDisplay) {
                fileNameDisplay.textContent = "Chưa chọn file";
                fileNameDisplay.style.color = "#999";
            }
            return;
        }
        const ext = f.name.substring(f.name.lastIndexOf("."));
        const base = f.name.replace(ext, "");
        if (fileNameDisplay) {
            fileNameDisplay.textContent = `✓ ${f.name} → ${base}_detect${ext} (${(f.size / 1024).toFixed(1)} KB)`;
            fileNameDisplay.style.color = "#44dd44";
        }
    });
}

// Điều khiển thanh trượt ( cấu hình Confidence & IOU )
if (confSlider) {
    confSlider.addEventListener("input", (e) => {
        if (confVal) confVal.textContent = e.target.value;
    });
}

if (iouSlider) {
    iouSlider.addEventListener("input", (e) => {
        if (iouVal) iouVal.textContent = e.target.value;
    });
}

// Chon ảnh và gửi form
if (form) {
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const f = imageInput.files[0];
        if (!f) {
            showError("Vui lòng chọn ảnh");
            return;
        }

        if (originalImg) {
            originalImg.src = URL.createObjectURL(f);
            originalImg.classList.add("active");
        }
        if (processedImg) {
            processedImg.classList.remove("active");
        }

        const fd = createUploadForm("image", f);
        await sendToUpload(fd);
    });
}
