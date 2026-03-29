// Frontend Script for YOLO Detection

// DOM Elements
const form = document.getElementById("yoloForm");
const imageInput = document.getElementById("imageInput");
const fileNameDisplay = document.getElementById("fileName");
const originalImg = document.getElementById("anhgoc");
const processedImg = document.getElementById("sauxuly");
const cameraPreview = document.getElementById("cameraPreview");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");

// UI Functions
function uiStart() {
    loading.style.display = "block";
    form.querySelector(".btn-primary").disabled = true;
}

function uiEnd() {
    loading.style.display = "none";
    form.querySelector(".btn-primary").disabled = false;
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

// Update Functions
function updateDensity(count) {
    const total = document.getElementById("totalVehicles");
    const level = document.getElementById("densityLevel");
    total.textContent = count;
    if (count < 5) level.textContent = "🟢 Ít";
    else if (count <= 10) level.textContent = "🟡 Trung bình";
    else if (count <= 15) level.textContent = "🟠 Khá";
    else level.textContent = "🔴 Đông";
}

function updateLightTimes(g, y, r) {
    document.getElementById("greenTime").textContent = `${g}s`;
    document.getElementById("yellowTime").textContent = `${y}s`;
    document.getElementById("redTime").textContent = `${r}s`;
}

function showProcessedImage(url) {
    processedImg.onload = () => processedImg.classList.add("active");
    processedImg.src = url;
}

// Handle Response
function handleCaptureResponse(data) {
    let totalCount = 0;
    if (Array.isArray(data.xe_locals)) {
        data.xe_locals.forEach((c, i) => {
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
        showProcessedImage(data.yolo_image);
    }

    const yellow = data.yellow_seconds ?? 3;
    const total = data.total_seconds ?? data.red_seconds ?? 0;
    const red = total;
    const green = data.green_seconds ?? Math.max(0, red - yellow);
    updateLightTimes(green, yellow, red);
    showError("");
}

// API Calls
async function uploadfile() {
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

async function chupmanhinh() {
    uiStart();
    showError("");
    try {
        await uploadfile();
        const res = await fetch(`/camera_capture`, { method: "POST" });
        if (!res.ok) throw new Error("Lỗi server: " + res.status);
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        handleCaptureResponse(data);
        if (imageInput) {
            imageInput.value = "";
            fileNameDisplay.textContent = "Chưa chọn file";
            fileNameDisplay.style.color = "#999";
        }
    } catch (err) {
        showError("Lỗi: " + err.message);
    } finally {
        uiEnd();
    }
}

// Camera
function startCamera() {
    cameraPreview.src = "/camera_stream";
}

// Event Listeners
window.addEventListener("DOMContentLoaded", () => {
    startCamera();
});

cameraCaptureBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    if (imageInput) {
        imageInput.value = "";
        fileNameDisplay.textContent = "Chưa chọn file";
        fileNameDisplay.style.color = "#999";
    }
    await chupmanhinh();
});

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

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await chupmanhinh();
});
