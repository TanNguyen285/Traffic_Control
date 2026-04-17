/**
 * TRAFFIC CONTROL SYSTEM - REALTIME SSE VERSION
 */

const originalImg = document.getElementById("anhgoc");
const processedImg = document.getElementById("sauxuly");
const cameraCaptureBtn = document.getElementById("cameraCaptureBtn");
const loading = document.getElementById("loading");
const errorMessage = document.getElementById("errorMessage");
const modeStatus = document.getElementById("mode");

function showError(msg) {
    if (!errorMessage) return;
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

function capnhat_trangthai(cmd) {
    if (!modeStatus) return;
    let text = "";
    let className = "";

    switch (cmd) {
        case "A": case "B":
            text = "🔴 ĐÔNG (Ưu tiên xanh)";
            className = "status-heavy"; break;
        case "m2":
            text = "⚪ XẢ TRẠM (Khẩn cấp)";
            className = "status-emergency"; break;
        case "m1":
            text = "🟢 THÔNG THOÁNG";
            className = "status-low"; break;
        case "m3":
            text = "🟡 TRUNG BÌNH";
            className = "status-medium"; break;
        case "m4":
            text = "🟠 KHÁ ĐÔNG";
            className = "status-high"; break;
        default:
            text = "🔵 ĐANG ĐỢI DỮ LIỆU...";
            className = "";
    }
    modeStatus.textContent = text;
    modeStatus.className = className;
}

function time_light(g, y, r) {
    const gt = document.getElementById("greenTime");
    const yt = document.getElementById("yellowTime");
    const rt = document.getElementById("redTime");
    if(gt) gt.textContent = `${g}s`;
    if(yt) yt.textContent = `${y}s`;
    if(rt) rt.textContent = `${r}s`;
}

/**
 * HÀM HIỂN THỊ CHÍNH
 */
function xulyKetQua(data) {
    if (!data) return;

    // 1. Cập nhật số xe
    if (Array.isArray(data.counts)) {
        let totalCount = 0;
        data.counts.forEach((count, i) => {
            const el = document.getElementById(`count-${i}`);
            if (el) el.textContent = count;
            totalCount += count;
        });
        const totalEl = document.getElementById("tongxe");
        if (totalEl) totalEl.textContent = data.xe_local || totalCount;
    }

    // 2. Cập nhật CMD & Trạng thái
    if (data.final_cmd) capnhat_trangthai(data.final_cmd);

    // 3. Hiển thị Ảnh (Base64)
    if (data.input_image) {
        originalImg.src = data.input_image;
        originalImg.style.display = "block";
    }
    if (data.yolo_image) {
        processedImg.src = data.yolo_image;
        processedImg.style.display = "block";
    }

    // 4. Thời gian đèn
    const yellow = data.yellow_seconds || 3;
    const green = data.green_seconds || 30;
    const red = data.red_seconds || (green + yellow);
    time_light(green, yellow, red);

    // 5. Ánh sáng
    const brightnessEl = document.getElementById("brightness_val");
    if(brightnessEl) brightnessEl.textContent = data.brightness || "0";
    
    showError("");
}

/**
 * THIẾT LẬP KẾT NỐI REALTIME (SSE)
 */
function connectRealtime() {
    console.log("Đang kết nối luồng dữ liệu Realtime...");
    
    // Mở đường ống nhận dữ liệu từ Server
    const eventSource = new EventSource("/stream_results");

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log("Đã nhận kết quả AI mới tự động!");
            xulyKetQua(data);
        } catch (err) {
            console.error("Lỗi giải mã dữ liệu SSE:", err);
        }
    };

    eventSource.onerror = function(err) {
        console.warn("Mất kết nối SSE. Đang thử kết nối lại sau 5s...");
        eventSource.close();
        setTimeout(connectRealtime, 5000); // Thử kết nối lại nếu rớt mạng
    };
}

// Khởi chạy kết nối khi trang web load xong
window.addEventListener("DOMContentLoaded", () => {
    connectRealtime();
});