
(function () {
    const POINT_RADIUS = 12;
    const DRAG_THRESHOLD = 28;
    const FILL_COLOR = "rgba(135, 206, 235, 0.30)";  // xanh biển nhạt
    const STROKE_COLOR = "#87CEEB";

    const img        = document.getElementById("cameraPreview");
    const canvas      = document.getElementById("roiCanvas");
    const drawBtn      = document.getElementById("roiDrawBtn");
    const editBar      = document.getElementById("roiEditBar");
    const saveBtn      = document.getElementById("roiSaveBtn");
    const cancelBtn    = document.getElementById("roiCancelBtn");

    if (!img || !canvas || !drawBtn) return; // phòng khi thiếu phần tử

    const ctx = canvas.getContext("2d");

    let editing      = false;
    let frameW = 0, frameH = 0;       // kích thước khung hình THẬT từ server
    let points = [];                  // toạ độ THẬT (server) — nguồn chân lý khi không edit
    let editPoints = [];              // toạ độ hiển thị (canvas) — nháp khi đang edit
    let draggingIdx = null;

    // ---------------------------------------------------------------- utils
    function syncCanvasSize() {
        const rect = img.getBoundingClientRect();
        canvas.width  = rect.width;
        canvas.height = rect.height;
    }

    function getContentRect() {
        // object-fit:contain co ảnh lại để giữ tỉ lệ, sinh ra viền đen 2 bên
        // (hoặc trên/dưới) nếu tỉ lệ khung hình thật khác tỉ lệ khung hiển thị.
        // Phải trừ phần viền đen này ra thì toạ độ điểm mới khớp đúng vị trí ảnh.
        const boxW = canvas.width, boxH = canvas.height;
        const imgAspect = frameW / frameH;
        const boxAspect = boxW / boxH;
        let renderW, renderH, offsetX, offsetY;
        if (imgAspect > boxAspect) {
            renderW = boxW;
            renderH = boxW / imgAspect;
            offsetX = 0;
            offsetY = (boxH - renderH) / 2;
        } else {
            renderH = boxH;
            renderW = boxH * imgAspect;
            offsetY = 0;
            offsetX = (boxW - renderW) / 2;
        }
        return { renderW, renderH, offsetX, offsetY };
    }

    function toDisplay(pt) {
        // toạ độ khung hình thật -> toạ độ canvas (đang hiển thị)
        const { renderW, renderH, offsetX, offsetY } = getContentRect();
        return [
            offsetX + (pt[0] / frameW) * renderW,
            offsetY + (pt[1] / frameH) * renderH,
        ];
    }

    function toReal(pt) {
        // toạ độ canvas -> toạ độ khung hình thật
        const { renderW, renderH, offsetX, offsetY } = getContentRect();
        return [
            Math.round(((pt[0] - offsetX) / renderW) * frameW),
            Math.round(((pt[1] - offsetY) / renderH) * frameH),
        ];
    }

    function drawOverlay() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (!editPoints.length) return;

        ctx.beginPath();
        editPoints.forEach(([x, y], i) => {
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.closePath();
        ctx.fillStyle = FILL_COLOR;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = STROKE_COLOR;
        ctx.stroke();

        editPoints.forEach(([x, y], i) => {
            ctx.beginPath();
            ctx.arc(x, y, POINT_RADIUS, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff";
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = STROKE_COLOR;
            ctx.stroke();
            ctx.fillStyle = "#14283a";
            ctx.font = "11px sans-serif";
            ctx.fillText(String(i), x - 3, y + 4);
        });
    }

    // ------------------------------------------------------------ API calls
    async function fetchRoiPoints() {
        const res = await fetch("/roi_points");
        if (!res.ok) throw new Error("Khong lay duoc ROI hien tai");
        const data = await res.json();
        points = data.points;
        frameW = data.frame_w;
        frameH = data.frame_h;
    }

    async function saveRoiPoints(realPts) {
        const res = await fetch("/roi_points", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ points: realPts }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || "Luu ROI that bai");
        }
    }

    // ------------------------------------------------------------- editing
    async function enterEditMode() {
        try {
            await fetchRoiPoints(); // chỉ cần frame_w/frame_h để quy đổi lúc lưu, bỏ qua points trả về
        } catch (e) {
            console.error(e);
            // Không lấy được frame size từ server -> dùng tạm 640x480 (camera thật của bạn)
            frameW = 640;
            frameH = 480;
        }
        syncCanvasSize();

        // 8 điểm tụ thành 1 ô vuông nhỏ giữa canvas -> tự kéo ra theo ý muốn,
        // không phụ thuộc default phức tạp dễ bị lệch do letterbox/tỉ lệ khung hình.
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const half = 45; // nửa cạnh ô vuông nhỏ (px trên canvas) — giãn rộng hơn cho dễ bấm trúng từng điểm
        editPoints = [
            [cx - half, cy - half], // 0 góc trên-trái
            [cx,        cy - half], // 1 giữa cạnh trên
            [cx + half, cy - half], // 2 góc trên-phải
            [cx + half, cy],        // 3 giữa cạnh phải
            [cx + half, cy + half], // 4 góc dưới-phải
            [cx,        cy + half], // 5 giữa cạnh dưới
            [cx - half, cy + half], // 6 góc dưới-trái
            [cx - half, cy],        // 7 giữa cạnh trái
        ];

        editing = true;
        canvas.classList.add("editing");
        drawBtn.classList.add("active");
        drawBtn.textContent = "✏️ Đang vẽ...";
        editBar.style.display = "flex";
        drawOverlay();
    }

    function exitEditMode() {
        editing = false;
        draggingIdx = null;
        canvas.classList.remove("editing");
        drawBtn.classList.remove("active");
        drawBtn.textContent = "🎯 Vẽ ROI";
        editBar.style.display = "none";
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    async function handleSave() {
        const realPts = editPoints.map(toReal);
        try {
            await saveRoiPoints(realPts);
            exitEditMode();
        } catch (e) {
            console.error(e);
            alert("Lỗi khi lưu ROI: " + e.message);
        }
    }

    function handleCancel() {
        exitEditMode();
    }

    // --------------------------------------------------------------- mouse
    function getCanvasPos(evt) {
        const rect = canvas.getBoundingClientRect();
        return [evt.clientX - rect.left, evt.clientY - rect.top];
    }

    function nearestPointIdx([x, y]) {
        let bestIdx = -1, bestDist = Infinity;
        editPoints.forEach(([px, py], i) => {
            const d = Math.hypot(px - x, py - y);
            if (d < bestDist) { bestDist = d; bestIdx = i; }
        });
        return bestDist < DRAG_THRESHOLD ? bestIdx : -1;
    }

    canvas.addEventListener("mousedown", (evt) => {
        if (!editing) return;
        const pos = getCanvasPos(evt);
        const idx = nearestPointIdx(pos);
        if (idx !== -1) draggingIdx = idx;
    });

    canvas.addEventListener("mousemove", (evt) => {
        if (!editing || draggingIdx === null) return;
        editPoints[draggingIdx] = getCanvasPos(evt);
        drawOverlay();
    });

    window.addEventListener("mouseup", () => {
        draggingIdx = null;
    });

    // Hỗ trợ cảm ứng (tablet/điện thoại)
    canvas.addEventListener("touchstart", (evt) => {
        if (!editing) return;
        const t = evt.touches[0];
        const rect = canvas.getBoundingClientRect();
        const pos = [t.clientX - rect.left, t.clientY - rect.top];
        const idx = nearestPointIdx(pos);
        if (idx !== -1) { draggingIdx = idx; evt.preventDefault(); }
    }, { passive: false });

    canvas.addEventListener("touchmove", (evt) => {
        if (!editing || draggingIdx === null) return;
        const t = evt.touches[0];
        const rect = canvas.getBoundingClientRect();
        editPoints[draggingIdx] = [t.clientX - rect.left, t.clientY - rect.top];
        drawOverlay();
        evt.preventDefault();
    }, { passive: false });

    canvas.addEventListener("touchend", () => { draggingIdx = null; });

    // ------------------------------------------------------------ buttons
    drawBtn.addEventListener("click", () => {
        if (editing) exitEditMode();
        else enterEditMode();
    });
    saveBtn.addEventListener("click", handleSave);
    cancelBtn.addEventListener("click", handleCancel);

    // Ảnh stream (MJPEG) không phát sự kiện 'resize', nhưng cửa sổ trình duyệt thì có
    window.addEventListener("resize", () => {
        if (!editing) return;
        // Giữ nguyên toạ độ THẬT, chỉ vẽ lại theo kích thước hiển thị mới
        const realPts = editPoints.map(toReal);
        syncCanvasSize();
        editPoints = realPts.map(toDisplay);
        drawOverlay();
    });
})();