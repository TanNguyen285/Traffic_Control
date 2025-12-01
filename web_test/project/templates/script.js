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
const downloadBtn = document.getElementById("downloadBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");

// Status Lights
const statusRed = document.getElementById("statusRed");
const statusYellow = document.getElementById("statusYellow");
const statusGreen = document.getElementById("statusGreen");

// Time Display
const timeDisplay = document.getElementById("timeDisplay");

// ==========================================
// STATUS LIGHT CONTROL
// ==========================================
function setStatus(status) {
    statusRed.classList.remove("active");
    statusYellow.classList.remove("active");
    statusGreen.classList.remove("active");

    if (status === "ready") {
        statusGreen.classList.add("active");
    } else if (status === "processing") {
        statusYellow.classList.add("active");
    } else if (status === "error") {
        statusRed.classList.add("active");
    }
}

// ==========================================
// TIME DISPLAY
// ==========================================
let startTime = null;
let timerInterval = null;

function startTimer() {
    startTime = Date.now();
    if (timerInterval) clearInterval(timerInterval);
    
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const hours = String(Math.floor(elapsed / 3600)).padStart(2, "0");
        const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
        const seconds = String(elapsed % 60).padStart(2, "0");
        timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
    }, 100);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timeDisplay.textContent = "00:00:00";
}

// Initialize time display
setStatus("ready");
timeDisplay.textContent = "00:00:00";

// ==========================================
// FILE INPUT HANDLING
// ==========================================
imageInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
        fileNameDisplay.textContent = `✓ ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
        fileNameDisplay.style.color = "#44dd44";
    } else {
        fileNameDisplay.textContent = "Chưa chọn file";
        fileNameDisplay.style.color = "#999";
    }
});

// ==========================================
// SLIDER UPDATES
// ==========================================
confSlider.addEventListener("input", (e) => {
    confVal.textContent = e.target.value;
});

iouSlider.addEventListener("input", (e) => {
    iouVal.textContent = e.target.value;
});

// ==========================================
// FORM SUBMISSION
// ==========================================
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = imageInput.files[0];
    if (!file) {
        showError("Vui lòng chọn một file ảnh");
        setStatus("error");
        return;
    }

    // Preview original image
    originalImg.src = URL.createObjectURL(file);
    originalImg.classList.add("active");
    processedImg.classList.remove("active");

    // Show loading, hide error
    loading.style.display = "block";
    errorMessage.style.display = "none";
    form.querySelector(".btn-primary").disabled = true;

    // Start timer and set status
    startTimer();
    setStatus("processing");

    const formData = new FormData();
    formData.append("image", file);
    formData.append("conf", confSlider.value);
    formData.append("iou", iouSlider.value);

    try {
        const res = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }

        const data = await res.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Display processed image with cache buster
        const imageUrl = data.processed_image_url + '?t=' + Date.now();
        processedImg.onload = () => {
            console.log("Processed image loaded successfully");
        };
        processedImg.onerror = () => {
            console.error("Failed to load processed image:", imageUrl);
            showError("Không thể tải ảnh xử lý. URL: " + imageUrl);
        };
        processedImg.src = imageUrl;
        processedImg.classList.add("active");
        downloadBtn.href = data.processed_image_url;

        // Success
        setStatus("ready");
        showError(""); // Clear error

    } catch (err) {
        console.error("Error:", err);
        showError(`Lỗi: ${err.message}`);
        setStatus("error");
    } finally {
        loading.style.display = "none";
        form.querySelector(".btn-primary").disabled = false;
        stopTimer();
    }
});

// ==========================================
// ERROR DISPLAY
// ==========================================
function showError(message) {
    if (message) {
        errorMessage.textContent = message;
        errorMessage.style.display = "block";
    } else {
        errorMessage.style.display = "none";
    }
}
