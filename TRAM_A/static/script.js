/**
 * TRAFFIC CONTROL SYSTEM - REALTIME SSE VERSION
 */
let traffic_chart = null; 
let is_history_loaded = false; 

const originalImg = document.getElementById("anhgoc");
const processedImg = document.getElementById("sauxuly");
const modeStatus = document.getElementById("mode");
const totalxe = document.getElementById("tongxe");

// --- 1. KHỞI TẠO BIỂU ĐỒ ---
function initChart() {
    const ctx = document.getElementById('chart_live');
    if (!ctx) return;

    traffic_chart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Tổng số xe',
                data: [],
                detailedCounts: [],
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.2)',
                borderWidth: 3,
                pointRadius: 5,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
            plugins: {
                tooltip: {
                    callbacks: {
                        footer: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            const cls = traffic_chart.data.datasets[0].detailedCounts[index];
                            if (!cls) return '';
                            return ['', `🚌 Bus: ${cls[0]}`, `🚗 Car: ${cls[1]}`, `🛵 Motor: ${cls[2]}`, `🚛 Truck: ${cls[3]}`, `🚐 Van: ${cls[4]}`].join('\n');
                        }
                    }
                }
            }
        }
    });
}

// --- 2. HÀM ĐẨY DỮ LIỆU VÀO CHART ---
function pushToChart(item) {
    if (!traffic_chart || !item) return;
    const ds = traffic_chart.data.datasets[0];
    const labels = traffic_chart.data.labels;

    const displayTime = item.time || new Date().toLocaleTimeString('it-IT');

    // TẠM THỜI COMMENT DÒNG NÀY ĐỂ TEST:
    // if (labels.length > 0 && labels[labels.length - 1] === displayTime) return;

    labels.push(displayTime);
    ds.data.push(item.xe_local || 0);
    ds.detailedCounts.push(item.counts || [0,0,0,0,0]);

    if (labels.length > 50) {
        labels.shift();
        ds.data.shift();
        ds.detailedCounts.shift();
    }
}

// --- 3. HÀM ĐIỀU PHỐI CHÍNH (Xử lý SSE Data) ---
function xulyKetQua(dataRaw) {
    if (!dataRaw) return;

    if (Array.isArray(dataRaw)) {
        // Nạp lịch sử ban đầu
        if (!is_history_loaded) {
            console.log("Nạp lịch sử từ SSE...");
            dataRaw.forEach(item => pushToChart(item));
            is_history_loaded = true;
            if (traffic_chart) traffic_chart.update();
        }
    } else {
        // Cập nhật Realtime cho các biến text và ảnh
        console.log("Cập nhật UI từ SSE...");
        if (totalxe) totalxe.textContent = dataRaw.xe_local ?? "0";
        if (dataRaw.final_cmd) capnhat_trangthai(dataRaw.final_cmd);
        
        // Cập nhật ảnh
        updateImages("/static/current_input.jpg", "/static/current_yolo.jpg");

        // Yêu cầu quan trọng: Tự đọc file JSON vật lý để cập nhật Chart
        fetchAndProcessJSON();
    }
}

// --- 4. HÀM ĐỌC FILE JSON VẬT LÝ (Chỉ dành cho Chart) ---
async function fetchAndProcessJSON() {
    try {
        // Thêm timestamp để chắc chắn không bị dính cache trình duyệt
        const response = await fetch("/get_log_data?v=" + Date.now());
        const data = await response.json();
        
        console.log("Dữ liệu nhận từ RAM Server:", data);

        if (Array.isArray(data) && data.length > 0) {
            const latest_item = data[data.length - 1];
            
            // Đẩy vào biểu đồ
            pushToChart(latest_item);
            
            // Vẽ lại biểu đồ ngay lập tức
            if (traffic_chart) {
                traffic_chart.update('none'); 
            }
        }
    } catch (err) {
        console.error("Lỗi Fetch dữ liệu:", err);
    }
}

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

function capnhat_trangthai(cmd) {
    if (!modeStatus) return;
    let text = "", className = "";
    switch (cmd) {
        case "A": case "B": text = "🔴 ĐÔNG (Ưu tiên xanh)"; className = "status-heavy"; break;
        case "m2": text = "⚪ XẢ TRẠM (Khẩn cấp)"; className = "status-emergency"; break;
        case "m1": text = "🟢 THÔNG THOÁNG"; className = "status-low"; break;
        case "m3": text = "🟡 TRUNG BÌNH"; className = "status-medium"; break;
        case "m4": text = "🟠 KHÁ ĐÔNG"; className = "status-high"; break;
        default: text = "🔵 ĐANG ĐỢI DỮ LIỆU..."; className = "";
    }
    modeStatus.textContent = text;
    modeStatus.className = className;
}

// --- 5. KẾT NỐI SSE ---
function connectRealtime() {
    const eventSource = new EventSource("/stream_results?v=" + Date.now());

    eventSource.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            xulyKetQua(data);
        } catch (err) {
            console.error("Lỗi parse dữ liệu SSE:", err);
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        setTimeout(connectRealtime, 5000);
    };
}

window.addEventListener("DOMContentLoaded", () => {
    initChart();
    connectRealtime();
});