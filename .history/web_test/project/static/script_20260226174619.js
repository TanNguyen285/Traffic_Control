// =======================
//   FRONTEND MAIN SCRIPT 
//   (ĐÃ THÊM CHÚ THÍCH TIẾNG VIỆT)
//   KHÔNG CÒN AUTO-CYCLE
//   CHỈ CHỤP KHI NGƯỜI DÙNG BẤM NÚT
// =======================

// ====== LẤY CÁC PHẦN TỬ HTML ======
const form = document.getElementById("yoloForm");
const imageInput = document.getElementById("imageInput");
const fileNameDisplay = document.getElementById("fileName");

const originalImg = document.getElementById("originalImg");
const processedImg = document.getElementById("processedImg");
const cameraPreview = document.getElementById("cameraPreview");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");

const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");

const timeDisplay = document.getElementById("timeDisplay");

// ==============================================
//   BỘ ĐẾM THỜI GIAN XỬ LÝ (HIỆN 00:00:00)
// ==============================================
let timerInterval = null;
let startTime = null;

function startTimer() {
    startTime = Date.now();
    if (timerInterval) clearInterval(timerInterval);

    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
        const s = String(elapsed % 60).padStart(2, "0");
        timeDisplay.textContent = `${h}:${m}:${s}`;
    }, 200);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timeDisplay.textContent = "00:00:00";
}

// ==============================================
//      HIỆN LOADING + KHÓA NÚT BẤM
// ==============================================
function uiStart() {
    loading.style.display = "block";
    form.querySelector(".btn-primary").disabled = true;
    startTimer();
}

function uiEnd() {
    loading.style.display = "none";
    form.querySelector(".btn-primary").disabled = false;
    stopTimer();
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

// Tạo URL không cache
function noCache(url) {
    return url + "?t=" + Date.now();
}

// ==============================================
//   CẬP NHẬT MẬT ĐỘ XE TRÊN GIAO DIỆN
// ==============================================
function updateDensity(count) {
    const total = document.getElementById("totalVehicles");
    const level = document.getElementById("densityLevel");

    total.textContent = count;

    if (count < 5) level.textContent = "🟢 Ít";
    else if (count <= 10) level.textContent = "🟡 Trung bình";
    else if (count <= 15) level.textContent = "🟠 Khá";
    else level.textContent = "🔴 Đông";
}

// ==============================================
//   CẬP NHẬT THỜI GIAN ĐÈN TÍN HIỆU
// ==============================================
function updateLightTimes(g, y, r) {
    document.getElementById("greenTime").textContent = `${g}s`;
    document.getElementById("yellowTime").textContent = `${y}s`;
    document.getElementById("redTime").textContent = `${r}s`;
}

// ==============================================
//     HIỆN ẢNH ĐÃ XỬ LÝ
// ==============================================
function showProcessedImage(url) {
    processedImg.onload = () => processedImg.classList.add("active");
    processedImg.src = url;
}

// ==============================================
//   XỬ LÝ JSON TRẢ VỀ SAU KHI DETECT
// ==============================================
function handleCaptureResponse(data) {
    // ----------- Đếm xe -----------  
    let totalCount = 0;
    if (Array.isArray(data.counts)) {
        data.counts.forEach((c, i) => {
            const el = document.getElementById(`count-${i}`);
            if (el) el.textContent = c;
            totalCount += c;
        });
    }
    updateDensity(totalCount);

    // ----------- Ảnh gốc -----------  
    if (data.input_image) {
        originalImg.src = data.input_image;
        originalImg.classList.add("active");
    }

    // ----------- Ảnh detect -----------  
    if (data.processed_image) {
        showProcessedImage(data.processed_image);
    }

    // ----------- Thời gian đèn -----------
    const yellow = data.yellow_seconds ?? 3;
    const total = data.total_seconds ?? data.red_seconds ?? 0;
    const red = total;
    const green = data.green_seconds ?? Math.max(0, red - yellow);

    updateLightTimes(green, yellow, red);

    showError("");
}

// ==============================================
//   GỌI API /camera_capture (KHI BẤM NÚT)
// ==============================================
async function uploadFileIfNeeded() {
    if (imageInput && imageInput.files && imageInput.files.length > 0) {
        const file = imageInput.files[0];
        const fd = new FormData();
        fd.append('file', file);
        const upl = await fetch('/upload_image', { method: 'POST', body: fd });
        if (!upl.ok) throw new Error('Upload failed ' + upl.status);
        const j = await upl.json();
        if (j.error) throw new Error(j.error);
    }
}

async function captureFrameAndSend() {
    uiStart();
    showError("");

    try {
        await uploadFileIfNeeded();
        const res = await fetch(`/camera_capture`, { method: "POST" });
        if (!res.ok) throw new Error("Lỗi server: " + res.status);

        const data = await res.json();
        if (data.error) throw new Error(data.error);

        handleCaptureResponse(data);
        // reset file input after detection
        if (imageInput) {
            imageInput.value = "";
            fileNameDisplay.textContent = "Chưa chọn file";
            fileNameDisplay.style.color = "#999";
        }
    }
    catch (err) {
        showError("Lỗi: " + err.message);
    }
    finally {
        uiEnd();
    }
}

// ==============================================
//     HIỂN THỊ CAMERA STREAM LÊN TRANG
// ==============================================
function startCamera() {
    cameraPreview.src = "/camera_stream";
}

// ==============================================
//     SỰ KIỆN KHỞI TẠO TRANG
// ==============================================
window.addEventListener("DOMContentLoaded", () => {
    // Chỉ hiển thị camera – KHÔNG tự detect
    startCamera();
    // Bắt đầu polling file last_detection.json để cập nhật ảnh khi có detect từ UART
    startLastDetectionPolling();
});

// ==============================================
//     NÚT "📸 Chụp & Detect"
// ==============================================
cameraCaptureBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    await captureFrameAndSend();
});

// ==============================================
//     HIỂN THỊ TÊN FILE ẢNH (KHI UPLOAD)
// ==============================================
if (imageInput) {
    imageInput.addEventListener("change", () => {
        const f = imageInput.files[0];
        if (!f) {
            fileNameDisplay.textContent = "Chưa chọn file";
            fileNameDisplay.style.color = "#999";
            return;
        }
        fileNameDisplay.textContent = `✓ ${f.name}`;
        fileNameDisplay.style.color = "#44dd44";
    });
}

// ==============================================
//     CẬP NHẬT TEXT CHO SLIDER CONF & IOU
// ==============================================

// ==============================================
//     NÚT PHÂN TÍCH TRONG FORM (NẾU CÓ)
// ==============================================
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await captureFrameAndSend();
});

// ==========================
// Polling last_detection.json
// ==========================
let lastDetectionTimestamp = 0;
let lastPollInterval = null;

async function pollLastDetection() {
    try {
        const res = await fetch(noCache('/static/last_detection.json'));
        if (!res.ok) return;
        const data = await res.json();
        if (!data || !data.timestamp) return;
        if (data.timestamp > lastDetectionTimestamp) {
            lastDetectionTimestamp = data.timestamp;
            // Update UI using existing handler
            handleCaptureResponse(data);
        }
    } catch (e) {
        // ignore fetch errors (file may not exist yet)
    }
}

function startLastDetectionPolling(intervalMs = 2000) {
    if (lastPollInterval) return;
    // poll immediately, then set interval
    pollLastDetection();
    lastPollInterval = setInterval(pollLastDetection, intervalMs);
}

function stopLastDetectionPolling() {
    if (!lastPollInterval) return;
    clearInterval(lastPollInterval);
    lastPollInterval = null;
}
