const errorMessage = document.getElementById("errorMessage");

const streams = [
    {
        id: 1,
        endpoint: "/data_a",
        branchLetter: "A",
        processedImg: document.getElementById("processedImg1"),
        totalVehicles: document.getElementById("totalVehicles1"),
        statusGreen: document.getElementById("statusGreen1"),
        statusYellow: document.getElementById("statusYellow1"),
        statusRed: document.getElementById("statusRed1"),
        greenTime: document.getElementById("greenTime1"),
        yellowTime: document.getElementById("yellowTime1"),
        redTime: document.getElementById("redTime1")
    },
    {
        id: 2,
        endpoint: "/data_b",
        branchLetter: "B",
        processedImg: document.getElementById("processedImg2"),
        totalVehicles: document.getElementById("totalVehicles2"),
        statusGreen: document.getElementById("statusGreen2"),
        statusYellow: document.getElementById("statusYellow2"),
        statusRed: document.getElementById("statusRed2"),
        greenTime: document.getElementById("greenTime2"),
        yellowTime: document.getElementById("yellowTime2"),
        redTime: document.getElementById("redTime2")
    }
];

const branchTotals = { 1: 0, 2: 0 };

const streamState = {
    1: { lastTimestamp: 0, lastProcessedKey: "", inFlight: false, imageLoading: false },
    2: { lastTimestamp: 0, lastProcessedKey: "", inFlight: false, imageLoading: false }
};

let scheduledUI = false;
const uiQueue = [];

function queueUIUpdate(fn) {
    uiQueue.push(fn);
    if (scheduledUI) return;
    scheduledUI = true;
    requestAnimationFrame(() => {
        while (uiQueue.length > 0) {
            const cb = uiQueue.shift();
            cb();
        }
        scheduledUI = false;
    });
}

function noCache(url) {
    if (!url || url.startsWith("data:")) return url;
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}t=${Date.now()}`;
}

function showError(msg) {
    if (!errorMessage) return;
    errorMessage.textContent = msg;
    errorMessage.style.display = msg ? "block" : "none";
}

function setLightActive(stream, activeColor) {
    const map = {
        green: stream.statusGreen,
        yellow: stream.statusYellow,
        red: stream.statusRed
    };
    Object.entries(map).forEach(([color, el]) => {
        if (!el) return;
        if (color === activeColor) el.classList.add("active");
        else el.classList.remove("active");
    });
}

function setDiagramPostActive(postEl, activeColor) {
    if (!postEl) return;
    const bulbs = postEl.querySelectorAll(".diagram-bulb");
    bulbs.forEach((b) => {
        const c = b.dataset.bulb;
        if (c === activeColor) b.classList.add("is-active");
        else b.classList.remove("is-active");
    });
}

function applyP2PTrafficAndDiagram() {
    streams.forEach((stream) => {
        const total = branchTotals[stream.id];
        let color = "red";
        if (total <= 5) color = "green";
        else if (total <= 12) color = "yellow";
        else color = "red";

        queueUIUpdate(() => {
            setLightActive(stream, color);
            const post = document.getElementById(stream.id === 1 ? "diagramPostA" : "diagramPostB");
            setDiagramPostActive(post, color);
        });
    });
}

function buildCountElementMap(streamId) {
    const map = {};
    const classEls = document.querySelectorAll(`#countsGrid${streamId} .count-value`);
    classEls.forEach((el) => {
        const cls = (el.dataset.className || "").toLowerCase().replace(/\s+/g, "_");
        if (cls) map[cls] = el;
    });
    return map;
}

function normalizeCounts(data, streamId) {
    const counts = data.counts;
    const results = {};
    const stream = streams.find(s => s.id === streamId);
    const classKeys = Object.keys(stream?.countElements || {});

    if (Array.isArray(counts)) {
        counts.forEach((val, idx) => {
            const cls = classKeys[idx] || String(idx);
            results[cls] = Number(val) || 0;
        });
    } else if (typeof counts === "object") {
        Object.keys(counts).forEach((k) => {
            results[String(k).toLowerCase().replace(/\s+/g, "_")] = Number(counts[k]) || 0;
        });
    }
    return results;
}

function updateProcessedImage(stream, data, state) {
    const imagePath = data.processed_image;
    if (!imagePath || !stream.processedImg || state.imageLoading) return;

    // Fix lỗi: Không thêm noCache nếu là Base64
    const nextUrl = imagePath.startsWith("data:") ? imagePath : noCache(imagePath);

    state.imageLoading = true;
    const preloaded = new Image();
    preloaded.src = nextUrl;

    preloaded.onload = () => {
        queueUIUpdate(() => {
            stream.processedImg.src = nextUrl;
            stream.processedImg.classList.add("active");
            state.imageLoading = false;
        });
    };
    preloaded.onerror = () => { state.imageLoading = false; };
}

function updateStreamUI(stream, data) {
    const normalizedCounts = normalizeCounts(data, stream.id);
    let total = 0;

    Object.keys(normalizedCounts).forEach((cls) => {
        const value = normalizedCounts[cls];
        total += value;
        const countEl = stream.countElements?.[cls];
        if (countEl) countEl.textContent = String(value);
    });

    branchTotals[stream.id] = total;

    const yellow = Number(data.yellow_seconds ?? 3);
    const red = Number(data.red_seconds ?? data.total_seconds ?? 0);
    const green = Number(data.green_seconds ?? Math.max(0, red - yellow));

    queueUIUpdate(() => {
        if (stream.totalVehicles) stream.totalVehicles.textContent = String(total);
        if (stream.greenTime) stream.greenTime.textContent = `${green}s`;
        if (stream.yellowTime) stream.yellowTime.textContent = `${yellow}s`;
        if (stream.redTime) stream.redTime.textContent = `${red}s`;
    });

    updateProcessedImage(stream, data, streamState[stream.id]);
    applyP2PTrafficAndDiagram();
}

async function runStaticDetect() {
    const input = document.getElementById("inputStaticImageFile") || document.getElementById("staticImageInput");
    const branchSel = document.getElementById("selectDetectTargetBranch") || document.getElementById("staticTargetBranch");
    const file = input?.files?.[0];
    
    if (!file) {
        showError("Vui lòng chọn file ảnh trước.");
        return;
    }

    const streamId = Number(branchSel?.value || 1);
    const stream = streams.find((s) => s.id === streamId);
    showError("");

    const formData = new FormData();
    formData.append("image", file);

    try {
        const res = await fetch("/detect_static", { method: "POST", body: formData });
        if (res.ok) {
            const data = await res.json();
            // Ép UI cập nhật dữ liệu thật từ Python trả về
            updateStreamUI(stream, data);
        } else {
            throw new Error("Server báo lỗi khi xử lý ảnh.");
        }
    } catch (error) {
        showError("Lỗi Detect: " + error.message);
    }
}

function initCameraStreamSources() {
    const camera1 = document.getElementById("cameraPreview1");
    const camera2 = document.getElementById("cameraPreview2");
    if (camera1) camera1.src = "/video_feed";
    if (camera2) camera2.src = "/camera_stream_2";
}

function toggleIntegratedBranch(branchId) {
    const isA = String(branchId).toUpperCase() === "A" || branchId === 1;
    const panel = document.getElementById(isA ? "resultCollapsibleA" : "resultCollapsibleB");
    const btn = document.getElementById(isA ? "btnToggleResultsA" : "btnToggleResultsB");
    if (!panel || !btn) return;

    const open = panel.classList.toggle("is-open");
    btn.innerHTML = open ? '<span class="btn-toggle-icon">−</span> Thu gọn kết quả' : '<span class="btn-toggle-icon">+</span> Xem kết quả';
}

window.addEventListener("DOMContentLoaded", () => {
    streams.forEach((s) => {
        s.countElements = buildCountElementMap(s.id);
    });

    initCameraStreamSources();
    applyP2PTrafficAndDiagram();

    document.getElementById("btnToggleResultsA")?.addEventListener("click", () => toggleIntegratedBranch("A"));
    document.getElementById("btnToggleResultsB")?.addEventListener("click", () => toggleIntegratedBranch("B"));

    const fileInput = document.getElementById("inputStaticImageFile") || document.getElementById("staticImageInput");
    const fileNameEl = document.getElementById("textStaticFileName") || document.getElementById("staticFileName");
    fileInput?.addEventListener("change", () => {
        const f = fileInput.files?.[0];
        if (fileNameEl) fileNameEl.textContent = f ? `${f.name} (${Math.round(f.size / 1024)} KB)` : "Chưa chọn file";
    });

    const btnDetect = document.getElementById("btnDetectStaticImage") || document.getElementById("btnDetectStatic");
    btnDetect?.addEventListener("click", runStaticDetect);

    // TẠM TẮT AUTO POLL ĐỂ CHẠY UPLOAD
    console.log("🚀 Manual Mode: Polling disabled. Ready for upload.");
});