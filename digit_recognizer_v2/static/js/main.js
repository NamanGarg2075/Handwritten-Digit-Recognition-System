// ── Mode switching ─────────────────────────────────
document.querySelectorAll(".mode-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.add("hidden"));
    btn.classList.add("active");
    document.getElementById(`panel-${btn.dataset.mode}`).classList.remove("hidden");
  });
});

// ── Shared helpers ─────────────────────────────────
function showResult(panel, data) {
  const idle   = panel.querySelector(".result-idle-state");
  const active = panel.querySelector(".result-active");
  const digitEl = panel.querySelector(".big-digit");
  const confFill = panel.querySelector(".conf-fill");
  const confPct  = panel.querySelector(".conf-pct");
  const top3El   = panel.querySelector(".top3-list");
  const heatEl   = panel.querySelector(".heatmap");

  panel.classList.remove("loading");

  if (data.error) {
    idle.innerHTML = `<div class="idle-glyph">!</div><p>${data.error}</p>`;
    idle.classList.remove("hidden");
    active.classList.add("hidden");
    return;
  }

  idle.classList.add("hidden");
  active.classList.remove("hidden");

  // Big digit — re-trigger animation
  digitEl.textContent = data.digit;
  digitEl.style.animation = "none";
  requestAnimationFrame(() => { digitEl.style.animation = ""; });

  // Confidence
  confFill.style.width = data.confidence + "%";
  confPct.textContent  = data.confidence.toFixed(1) + "%";

  // Top-3
  if (top3El && data.top3) {
    top3El.innerHTML = data.top3.map((item, i) => `
      <div class="top3-item ${i === 0 ? 'rank-1' : ''}">
        <div class="top3-d">${item.digit}</div>
        <div class="top3-p">${item.prob.toFixed(1)}%</div>
      </div>
    `).join("");
  }

  // Heatmap (all 10 digits)
  if (heatEl && data.probabilities) {
    const maxProb = Math.max(...Object.values(data.probabilities));
    heatEl.innerHTML = Array.from({ length: 10 }, (_, d) => {
      const p = data.probabilities[d] ?? 0;
      const isTop = p === maxProb;
      return `
        <div class="heat-cell ${isTop ? 'top' : ''}">
          <div class="heat-bg" style="height:${p}%"></div>
          <span class="heat-d">${d}</span>
          <span class="heat-p">${p.toFixed(0)}%</span>
        </div>
      `;
    }).join("");
  }
}

function setLoading(panel) {
  const idle   = panel.querySelector(".result-idle-state");
  const active = panel.querySelector(".result-active");
  const digitEl = panel.querySelector(".big-digit");
  idle.classList.add("hidden");
  active.classList.remove("hidden");
  panel.classList.add("loading");
  if (digitEl) digitEl.textContent = "…";
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ═══════════════════════════════════════════════════
//  CANVAS
// ═══════════════════════════════════════════════════
const canvas      = document.getElementById("drawCanvas");
const ctx         = canvas.getContext("2d");
const canvasPanel = document.getElementById("canvasResult");
const brushSlider = document.getElementById("brushSize");
const brushValEl  = document.getElementById("brushVal");

let drawing = false, lastX = 0, lastY = 0, hasDrawn = false, realtimeTimer = null;
let dpr = 1;

function initCanvas() {
  dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();

  canvas.width  = Math.round(rect.width  * dpr);
  canvas.height = Math.round(rect.height * dpr);


  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);

  clearCanvas();
}

function clearCanvas() {
  const w = canvas.width  / dpr;
  const h = canvas.height / dpr;
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, w, h);
}

function getBrushSize() {
  return parseInt(brushSlider.value, 10);
}

brushSlider.addEventListener("input", () => {
  brushValEl.textContent = brushSlider.value;
});

function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  if (e.touches) return {
    x: e.touches[0].clientX - rect.left,
    y: e.touches[0].clientY - rect.top,
  };
  return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

canvas.addEventListener("mousedown",  startDraw);
canvas.addEventListener("mousemove",  draw);
canvas.addEventListener("mouseup",    stopDraw);
canvas.addEventListener("mouseleave", stopDraw);
canvas.addEventListener("touchstart", startDraw, { passive: false });
canvas.addEventListener("touchmove",  draw,      { passive: false });
canvas.addEventListener("touchend",   stopDraw);

function startDraw(e) {
  e.preventDefault();
  drawing = true;
  const pos = getPos(e);
  lastX = pos.x; lastY = pos.y;
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, getBrushSize() / 2, 0, Math.PI * 2);
  ctx.fillStyle = "#ffffff"; 
  ctx.fill();
  hasDrawn = true;
}

function draw(e) {
  if (!drawing) return;
  e.preventDefault();
  const pos = getPos(e);
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(pos.x, pos.y);
  ctx.strokeStyle = "#ffffff";  
  ctx.lineWidth   = getBrushSize();
  ctx.lineCap     = "round";
  ctx.lineJoin    = "round";
  ctx.stroke();
  lastX = pos.x; lastY = pos.y;

  clearTimeout(realtimeTimer);
  realtimeTimer = setTimeout(predictCanvas, 300);
}

function stopDraw(e) {
  if (!drawing) return;
  drawing = false;
  clearTimeout(realtimeTimer);
  if (hasDrawn) predictCanvas();
}

async function predictCanvas() {
  if (!hasDrawn) return;
  setLoading(canvasPanel);
  try {
    const data = await postJSON("/predict/canvas", { image: canvas.toDataURL("image/png") });
    showResult(canvasPanel, data);
  } catch {
    showResult(canvasPanel, { error: "Server unreachable — is Flask running?" });
  }
}

document.getElementById("clearBtn").addEventListener("click", () => {
  clearCanvas();
  hasDrawn = false;
  const idle   = canvasPanel.querySelector(".result-idle-state");
  const active = canvasPanel.querySelector(".result-active");
  idle.innerHTML = `<div class="idle-glyph">?</div><p>Draw a digit to begin analysis</p>`;
  idle.classList.remove("hidden");
  active.classList.add("hidden");
  canvasPanel.classList.remove("loading");
});

document.getElementById("predictBtn").addEventListener("click", predictCanvas);

window.addEventListener("load",   initCanvas);
window.addEventListener("resize", () => {
  initCanvas();
  hasDrawn = false;
});

// ═══════════════════════════════════════════════════
//  UPLOAD
// ═══════════════════════════════════════════════════
const fileInput   = document.getElementById("fileInput");
const dropZone    = document.getElementById("dropZone");
const previewImg  = document.getElementById("previewImg");
const previewWrap = document.getElementById("uploadPreviewWrap");
const uploadBtn   = document.getElementById("uploadPredictBtn");
const uploadPanel = document.getElementById("uploadResult");

function handleFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  previewImg.src = URL.createObjectURL(file);
  previewWrap.classList.remove("hidden");
  uploadBtn._file = file;
}

fileInput.addEventListener("change", () => handleFile(fileInput.files[0]));

dropZone.addEventListener("dragover",  e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  handleFile(e.dataTransfer.files[0]);
});

uploadBtn.addEventListener("click", async () => {
  const file = uploadBtn._file;
  if (!file) return;
  setLoading(uploadPanel);
  const form = new FormData();
  form.append("file", file);
  try {
    const res  = await fetch("/predict/upload", { method: "POST", body: form });
    const data = await res.json();
    showResult(uploadPanel, data);
  } catch {
    showResult(uploadPanel, { error: "Server unreachable — is Flask running?" });
  }
});
