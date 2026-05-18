/**
 * TRAFFIC CONTROL SYSTEM - REALTIME SSE VERSION
 */
let traffic_chart = null;
let is_history_loaded = false;
let current_mode = "single";

const originalImg  = document.getElementById("anhgoc");
const processedImg = document.getElementById("sauxuly");
const modeStatus   = document.getElementById("mode");
const totalxe      = document.getElementById("tongxe");
const brightnessEl = document.getElementById("brightness");

// --- 1. KHỞI TẠO BIỂU ĐỒ ---
function initChart() {
    const ctx = document.getElementById('chart_live');
    if (!ctx) return;

    traffic_chart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Số xe',
                data: [],
                detailedCounts: [],
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.15)',
                borderWidth: 2.5,
                pointRadius: 5,
                pointBackgroundColor: '#e74c3c',
                fill: true,
                tension: 0.3,
                spanGaps: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            return `Xe: ${ctx.parsed.y}`;
                        },
                        footer: function(tooltipItems) {
                            const idx = tooltipItems[0].dataIndex;
                            const cls = traffic_chart.data.datasets[0].detailedCounts[idx];
                            if (!cls) return '';
                            // YOLO_CLASSES = ['car','van','bus','motorcycle','truck']
                            return [
                                '',
                                `🚗 Car: ${cls[0]}`,
                                `🚐 Van: ${cls[1]}`,
                                `🚌 Bus: ${cls[2]}`,
                                `🛵 Motor: ${cls[3]}`,
                                `🚛 Truck: ${cls[4]}`
                            ].join('\n');
                        }
                    }
                }
            }
        }
    });
}

// --- 2. ĐẨY DỮ LIỆU VÀO CHART ---
function pushToChart(item) {
    if (!traffic_chart || !item) return;

    const ds     = traffic_chart.data.datasets[0];
    const labels = traffic_chart.data.labels;

    labels.push(item.time || new Date().toLocaleTimeString('it-IT'));
    ds.data.push(item.xe_local || 0);
    ds.detailedCounts.push(item.counts || [0, 0, 0, 0, 0]);

    if (labels.length > 50) {
        labels.shift();
        ds.data.shift();
        ds.detailedCounts.shift();
    }
}

// --- 3. XỬ LÝ SSE DATA ---
function xulyKetQua(dataRaw) {
    if (!dataRaw) return;

    // Lịch sử ban đầu
    if (Array.isArray(dataRaw)) {
        if (!is_history_loaded) {
            dataRaw.forEach(item => pushToChart(item));
            is_history_loaded = true;
            if (traffic_chart) traffic_chart.update();
        }
        return;
    }

    // Kết quả AI realtime
    if (totalxe) totalxe.textContent = dataRaw.xe_local ?? "0";
    if (brightnessEl) brightnessEl.textContent = (dataRaw.brightness ?? 0).toFixed(1);
    if (dataRaw.final_cmd) capnhat_trangthai(dataRaw.final_cmd, dataRaw.is_emergency ?? false);
    updateImages("/static/current_input.jpg", "/static/current_yolo.jpg");
    pushToChart(dataRaw);
    if (traffic_chart) traffic_chart.update('none');
}

// --- 4. CẬP NHẬT ẢNH ---
function updateImages(input_url, yolo_url) {
    const ts = Date.now();
    if (input_url && originalImg) {
        originalImg.src = input_url.split('?')[0] + "?t=" + ts;
        originalImg.classList.add('active');
    }
    if (yolo_url && processedImg) {
        processedImg.src = yolo_url.split('?')[0] + "?t=" + ts;
        processedImg.classList.add('active');
    }
}

// --- 5. CẬP NHẬT TRẠNG THÁI ---
function capnhat_trangthai(cmd, is_emergency = false) {
    if (!modeStatus) return;
    let text = "", className = "";
    switch (cmd) {
        case "A": case "B": text = "🔴 ĐÔNG (Ưu tiên xanh)"; className = "status-heavy";     break;
        case "m1":          text = "🟢 THÔNG THOÁNG";         className = "status-low";       break;
        case "m2":          
            if (is_emergency) {
                text = "⚪ XẢ TRẠM (Khẩn cấp)";
                className = "status-emergency";
            } else {
                text = "🟡 KẸT NHẸ (Mức 2)";
                className = "status-medium";
            }
            break;
        case "m3":          text = "🟠 KẸT TRUNG BÌNH (Mức 3)";  className = "status-high";      break;
        case "m4":          text = "🔴 KẸT NẶNG (Mức 4)";       className = "status-critical";  break;
        default:            text = "🔵 ĐANG ĐỢI DỮ LIỆU..."; className = "";
    }
    modeStatus.textContent = text;
    modeStatus.className = className;
}

// --- 6. KẾT NỐI SSE ---
function connectRealtime() {
    const eventSource = new EventSource("/stream_results?v=" + Date.now());

    eventSource.onmessage = (e) => {
        try {
            xulyKetQua(JSON.parse(e.data));
        } catch (err) {
            console.error("Lỗi parse SSE:", err);
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        setTimeout(connectRealtime, 5000);
    };
}

// --- 7. KHỞI ĐỘNG ---
window.addEventListener("DOMContentLoaded", () => {
    initChart();
    connectRealtime();

    const modeSingleBtn  = document.getElementById("modeSingleBtn");
    const modeBranchBtn  = document.getElementById("modeBranchBtn");
    const modeStatusText = document.getElementById("modeStatusText");

    const savedMode = localStorage.getItem("traffic_mode") || "single";
    setMode(savedMode, modeSingleBtn, modeBranchBtn, modeStatusText);

    modeSingleBtn?.addEventListener("click", () => {
        setMode("single", modeSingleBtn, modeBranchBtn, modeStatusText);
        sendModeToServer("single");
    });
    modeBranchBtn?.addEventListener("click", () => {
        setMode("branch", modeSingleBtn, modeBranchBtn, modeStatusText);
        sendModeToServer("branch");
    });
});

function setMode(mode, singleBtn, branchBtn, statusText) {
    current_mode = mode;
    localStorage.setItem("traffic_mode", mode);
    if (singleBtn) singleBtn.classList.toggle("active", mode === "single");
    if (branchBtn) branchBtn.classList.toggle("active", mode === "branch");
    if (statusText) {
        statusText.textContent = mode === "single"
            ? "Chế độ: Đơn (Độc lập - Không cần Ethernet)"
            : "Chế độ: Nhánh (2 Trạm - Cần Ethernet)";
    }
}

async function sendModeToServer(mode) {
    try {
        const response = await fetch("/set_mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode })
        });
        if (!response.ok) console.warn(`[SERVER] Lỗi gửi chế độ: ${response.status}`);
    } catch (err) {
        console.error("[SERVER] Lỗi gửi chế độ:", err);
    }
}