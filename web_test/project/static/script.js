// ==========================================
// GHI CHÚ  - FRONTEND
// File này điều khiển hành vi client-side (JS):
// - Bắt sự kiện chọn file, hiển thị preview ảnh gốc
// - Gửi Form tới API `/upload` (multipart/form-data)
// - Nhận JSON trả về: { processed_image_url, counts, total_seconds, status }
// - Khi ảnh xử lý tải xong sẽ: hiển thị ảnh, cập nhật ô đếm (6 lớp), cập nhật thời gian và đèn trạng thái
// ==========================================

// ==========================================
// DOM Elements
// Lấy ra toàn bộ các phần tử HTML cần dùng bằng ID
// NOTE: Các biến này liên kết trực tiếp với UI để cập nhật giao diện
// ==========================================
const form = document.getElementById("yoloForm");
const imageInput = document.getElementById("imageInput");
const fileNameDisplay = document.getElementById("fileName");

const confSlider = document.getElementById("confSlider");  // Slider điều chỉnh CONF
const iouSlider = document.getElementById("iouSlider");    // Slider điều chỉnh IOU
const confVal = document.getElementById("confVal");        // Hiển thị giá trị CONF
const iouVal = document.getElementById("iouVal");          // Hiển thị giá trị IOU

const originalImg = document.getElementById("originalImg");    // ảnh gốc preview
const processedImg = document.getElementById("processedImg");  // ảnh đã xử lý YOLO

const downloadBtn = document.getElementById("downloadBtn");    // nút download ảnh xử lý

const loading = document.getElementById("loading");            // animation loading
const errorMessage = document.getElementById("errorMessage");  // khung hiển thị lỗi

// Các đèn LED trạng thái
// NOTE: CSS có .active để bật/tắt
const statusRed = document.getElementById("statusRed");
const statusYellow = document.getElementById("statusYellow");
const statusGreen = document.getElementById("statusGreen");

// Hiển thị thời gian xử lý client/server
const timeDisplay = document.getElementById("timeDisplay");

// Lấy các ID cho hiển thị thời gian đèn (bên trong traffic-light-item)
// NOTE: Các ID này nằm bên trong các đèn và sẽ được cập nhật bởi server
// khi trả về red_seconds, yellow_seconds, green_seconds

// ==========================================
// STATUS LIGHT CONTROL - KHÔNG SỬ DỤNG NỮA
// NOTE: 3 đèn luôn sáng (class "active" luôn có trong HTML)
// Chỉ cập nhật thời gian hiển thị trên mỗi đèn
// ==========================================
function setStatus(status) {
    // Giữ nguyên - 3 đèn luôn có class "active" và luôn sáng
    // Hàm này giữ lại chỉ để tương thích (không làm gì cả)
}

// ==========================================
// TIME DISPLAY - CẬP NHẬT THỜI GIAN CHO CÁC ĐÈN
// NOTE: Cập nhật các ID #greenTime, #yellowTime, #redTime
// ==========================================
function updateLightTimes(greenSec, yellowSec, redSec) {
    // Cập nhật thời gian hiển thị trên mỗi đèn
    const elGreen = document.getElementById('greenTime');
    const elYellow = document.getElementById('yellowTime');
    const elRed = document.getElementById('redTime');
    
    if (elGreen) elGreen.textContent = `${greenSec}s`;
    if (elYellow) elYellow.textContent = `${yellowSec}s`;
    if (elRed) elRed.textContent = `${redSec}s`;
}

// ==========================================
// TIME DISPLAY — Đếm thời gian thực người dùng chờ xử lý
// NOTE: Đây là thời gian CLIENT đo (UX), không phải thời gian YOLO thật 100%
// ==========================================
let startTime = null;
let timerInterval = null;

function startTimer() {
    startTime = Date.now();

    if (timerInterval) clearInterval(timerInterval);

    // chạy mỗi 0.1 giây
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);

        // Chuyển elapsed giây → hh:mm:ss
        const hours = String(Math.floor(elapsed / 3600)).padStart(2, "0");
        const minutes = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
        const seconds = String(elapsed % 60).padStart(2, "0");

        timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
    }, 100);
}

function stopTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timeDisplay.textContent = "00:00:00";  // reset
}

// Khởi tạo giao diện
// 3 đèn luôn sáng (class "active" đã có trong HTML)

// ==========================================
// FILE INPUT HANDLING — xử lý khi chọn file ảnh
// Hiển thị preview tên file, kích thước, và tên file output detect
// ==========================================
imageInput.addEventListener("change", (e) => {
    const file = e.target.files[0];

    if (file) {
        // Tách tên file ra để tạo tên dạng xxx_detect.jpg
        const nameOnly = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
        const ext = file.name.substring(file.name.lastIndexOf('.'));
        const processedName = `${nameOnly}_detect${ext}`;

        // NOTE: Hiển thị tên file theo dạng: "✓ input.jpg → input_detect.jpg (512 KB)"
        fileNameDisplay.textContent = `✓ ${file.name} → ${processedName} (${(file.size / 1024).toFixed(2)} KB)`;
        fileNameDisplay.style.color = "#44dd44"; // xanh lá
    } else {
        fileNameDisplay.textContent = "Chưa chọn file";
        fileNameDisplay.style.color = "#999";
    }
});

// ==========================================
// SLIDER UPDATES — cập nhật số khi kéo slider CONF / IOU
// ==========================================
confSlider.addEventListener("input", (e) => {
    confVal.textContent = e.target.value; // NOTE: cập nhật realtime
});

iouSlider.addEventListener("input", (e) => {
    iouVal.textContent = e.target.value;
});

// ==========================================
// FORM SUBMISSION — Khi bấm nút Detect
// Gửi ảnh + conf + iou tới server bằng fetch()
// ==========================================
form.addEventListener("submit", async (e) => {
    e.preventDefault(); // chặn reload trang

    const file = imageInput.files[0];
    if (!file) {
        showError("Vui lòng chọn một file ảnh");
        return;
    }

    // Preview ảnh gốc
    // NOTE: createObjectURL tạo URL tạm cho file local
    originalImg.src = URL.createObjectURL(file);
    originalImg.classList.add("active");

    // Ẩn ảnh detect cũ
    processedImg.classList.remove("active");

    // Show loading bar
    loading.style.display = "block";
    errorMessage.style.display = "none";

    // Disable nút Detect để tránh spam
    form.querySelector(".btn-primary").disabled = true;

    // Bắt đầu đếm thời gian
    startTimer();

    // 3 đèn luôn sáng - không cần gọi setStatus()

    // FormData gửi dạng multipart/form-data
    const formData = new FormData();
    formData.append("image", file);
    formData.append("conf", confSlider.value);
    formData.append("iou", iouSlider.value);
            formData.append('image', file);

            // Lấy giá trị thời gian (s/xe) do người dùng nhập cho mỗi lớp: #persec-0 .. #persec-5
            // Gửi dưới dạng JSON string trong trường 'persec'
            const perSecs = [];
            for (let i = 0; i < 6; i++) {
                const el = document.getElementById(`persec-${i}`);
                let v = 0;
                if (el) {
                    v = Number(el.value) || 0;
                }
                perSecs.push(v);
            }
            formData.append('persec', JSON.stringify(perSecs));
            // Thêm các tham số conf, iou từ slider (nếu cần server sử dụng)
            const conf = document.getElementById('confSlider')?.value || '0.5';
            const iou = document.getElementById('iouSlider')?.value || '0.5';
            formData.append('conf', conf);
            formData.append('iou', iou);
    try {
        // Gửi request đến /upload
        const res = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);

        // Nhận JSON trả về
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        // NOTE: thêm timestamp để tránh cache ảnh cũ
        const imageUrl = data.processed_image_url + '?t=' + Date.now();

        // Khi ảnh xử lý load xong thì mới hiện
        processedImg.onload = () => {
            processedImg.classList.add("active");
            downloadBtn.href = data.processed_image_url; // link download file detect

            // Cập nhật ô đếm 6 lớp (counts[0..5])
            if (data.counts && Array.isArray(data.counts)) {
                data.counts.slice(0,6).forEach((c, idx) => {
                    const el = document.getElementById(`count-${idx}`);
                    if (el) el.textContent = c;
                });
            }

            // Nếu server cung cấp thời gian tính toán thật → cập nhật các đèn
            if (typeof data.red_seconds === 'number') {
                const r = Number(data.red_seconds);
                const y = Number(data.yellow_seconds || 3);
                const g = Number(data.green_seconds || Math.max(0, r - y));
                updateLightTimes(g, y, r);  // Cập nhật thời gian trên 3 đèn
            }

            // Không gọi setStatus() nữa - 3 đèn luôn sáng
        };

        // Xử lý lỗi khi load ảnh detect fail
        processedImg.onerror = () => {
            showError("Không thể tải ảnh xử lý (404 hoặc server chưa ghi file).");
        };

        processedImg.src = imageUrl; // load ảnh detect

        showError("");

    } catch (err) {
        console.error("Error:", err);
        showError(`Lỗi: ${err.message}`);
        setStatus("error");
    } finally {
        loading.style.display = "none";
        form.querySelector(".btn-primary").disabled = false;
        stopTimer(); // reset timer
    }
});

// ==========================================
// ERROR DISPLAY — Hàm hiển thị lỗi UI
// ==========================================
function showError(message) {
    if (message) {
        errorMessage.textContent = message;
        errorMessage.style.display = "block";
    } else {
        errorMessage.style.display = "none";
    }
}
