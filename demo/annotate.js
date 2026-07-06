(function () {
  "use strict";

  var API_BASE = "";
  if (window.location.port === "8000") {
    API_BASE = "";
  } else {
    API_BASE = "http://localhost:8000";
  }

  var imageInput = document.getElementById("imageInput");
  var canvas = document.getElementById("annotateCanvas");
  var ctx = canvas.getContext("2d");
  var clearBoxBtn = document.getElementById("clearBoxBtn");
  var drawStatus = document.getElementById("drawStatus");
  var sampleIdInput = document.getElementById("sampleIdInput");
  var titleInput = document.getElementById("titleInput");
  var sceneTypeSelect = document.getElementById("sceneTypeSelect");
  var objectsInput = document.getElementById("objectsInput");
  var summaryInput = document.getElementById("summaryInput");
  var riskTypeSelect = document.getElementById("riskTypeSelect");
  var levelSelect = document.getElementById("levelSelect");
  var riskObjectsInput = document.getElementById("riskObjectsInput");
  var locationInput = document.getElementById("locationInput");
  var reasonInput = document.getElementById("reasonInput");
  var suggestionInput = document.getElementById("suggestionInput");
  var addRiskBtn = document.getElementById("addRiskBtn");
  var exportBtn = document.getElementById("exportBtn");
  var saveBtn = document.getElementById("saveBtn");
  var saveStatus = document.getElementById("saveStatus");
  var riskList = document.getElementById("riskList");

  var currentImage = null;
  var selectedFile = null;
  var imageUrl = "";
  var currentBox = null;
  var risks = [];
  var drawing = false;
  var startPoint = null;
  var riskRules = [];

  function init() {
    loadRiskRules();
    drawPlaceholder();
    imageInput.addEventListener("change", onImageChange);
    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", onMouseUp);
    clearBoxBtn.addEventListener("click", function () {
      currentBox = null;
      redraw();
    });
    addRiskBtn.addEventListener("click", addRisk);
    exportBtn.addEventListener("click", exportJson);
    saveBtn.addEventListener("click", saveToDataset);
  }

  function loadRiskRules() {
    fetch(API_BASE + "/api/risk_rules")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        riskRules = data.rules || [];
        renderRiskOptions();
      })
      .catch(function () {
        riskRules = [
          { risk_type: "electric_shock", risk_name: "触电风险" },
          { risk_type: "fire", risk_name: "火灾风险" },
          { risk_type: "trip", risk_name: "通行/绊倒风险" },
          { risk_type: "falling_object", risk_name: "坠物风险" },
          { risk_type: "dangerous_object", risk_name: "危险物暴露" },
          { risk_type: "cleanliness", risk_name: "清洁度异常" },
        ];
        renderRiskOptions();
      });
  }

  function renderRiskOptions() {
    riskTypeSelect.innerHTML = "";
    riskRules.forEach(function (rule) {
      var opt = document.createElement("option");
      opt.value = rule.risk_type || rule.risk_name || "";
      opt.dataset.name = rule.risk_name || rule.risk_type || "";
      opt.dataset.ruleId = rule.rule_id || "";
      opt.textContent = rule.risk_name || rule.risk_type || "";
      riskTypeSelect.appendChild(opt);
    });
  }

  function onImageChange(e) {
    var file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/") && !file.name.toLowerCase().endsWith(".svg")) {
      setStatus("请选择图片文件。", true);
      return;
    }

    selectedFile = file;
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    imageUrl = URL.createObjectURL(file);
    currentImage = new Image();
    currentImage.onload = function () {
      canvas.width = currentImage.naturalWidth || currentImage.width;
      canvas.height = currentImage.naturalHeight || currentImage.height;
      if (!sampleIdInput.value.trim()) {
        sampleIdInput.value = sanitizeId(file.name.replace(/\.[^.]+$/, ""));
      }
      if (!titleInput.value.trim()) {
        titleInput.value = file.name.replace(/\.[^.]+$/, "");
      }
      currentBox = null;
      risks = [];
      redraw();
      renderRiskList();
      setStatus("图片已加载，可以拖拽框选风险区域。");
    };
    currentImage.onerror = function () {
      setStatus("图片加载失败。", true);
    };
    currentImage.src = imageUrl;
  }

  function onMouseDown(e) {
    if (!currentImage) return;
    drawing = true;
    startPoint = getCanvasPoint(e);
    currentBox = { x: startPoint.x, y: startPoint.y, w: 0, h: 0 };
  }

  function onMouseMove(e) {
    if (!drawing || !startPoint) return;
    var point = getCanvasPoint(e);
    currentBox = normalizeBox({
      x: startPoint.x,
      y: startPoint.y,
      w: point.x - startPoint.x,
      h: point.y - startPoint.y,
    });
    redraw();
  }

  function onMouseUp() {
    if (!drawing) return;
    drawing = false;
    startPoint = null;
    if (currentBox && (currentBox.w < 4 || currentBox.h < 4)) {
      currentBox = null;
    }
    redraw();
  }

  function getCanvasPoint(e) {
    var rect = canvas.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(canvas.width, (e.clientX - rect.left) * canvas.width / rect.width)),
      y: Math.max(0, Math.min(canvas.height, (e.clientY - rect.top) * canvas.height / rect.height)),
    };
  }

  function normalizeBox(box) {
    var x = box.w < 0 ? box.x + box.w : box.x;
    var y = box.h < 0 ? box.y + box.h : box.y;
    var w = Math.abs(box.w);
    var h = Math.abs(box.h);
    x = Math.max(0, Math.min(canvas.width, x));
    y = Math.max(0, Math.min(canvas.height, y));
    w = Math.min(w, canvas.width - x);
    h = Math.min(h, canvas.height - y);
    return { x: x, y: y, w: w, h: h };
  }

  function toNormalizedBbox(box) {
    if (!box) return null;
    return [
      round4(box.x / canvas.width),
      round4(box.y / canvas.height),
      round4(box.w / canvas.width),
      round4(box.h / canvas.height),
    ];
  }

  function fromNormalizedBbox(bbox) {
    return {
      x: bbox[0] * canvas.width,
      y: bbox[1] * canvas.height,
      w: bbox[2] * canvas.width,
      h: bbox[3] * canvas.height,
    };
  }

  function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (currentImage) {
      ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);
    } else {
      drawPlaceholder();
      return;
    }

    risks.forEach(function (risk, index) {
      if (risk.bbox) drawBox(fromNormalizedBbox(risk.bbox), "#b91c1c", "R" + (index + 1));
    });
    if (currentBox) drawBox(currentBox, "#2563eb", "当前");
  }

  function drawPlaceholder() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#64748b";
    ctx.font = "20px Microsoft YaHei, Arial";
    ctx.textAlign = "center";
    ctx.fillText("选择图片开始标注", canvas.width / 2, canvas.height / 2);
  }

  function drawBox(box, color, label) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, canvas.width / 500);
    ctx.fillStyle = "rgba(185, 28, 28, 0.12)";
    ctx.fillRect(box.x, box.y, box.w, box.h);
    ctx.strokeRect(box.x, box.y, box.w, box.h);
    ctx.fillStyle = color;
    ctx.fillRect(box.x, Math.max(0, box.y - 24), Math.max(54, label.length * 16), 24);
    ctx.fillStyle = "#fff";
    ctx.font = "14px Microsoft YaHei, Arial";
    ctx.textAlign = "left";
    ctx.fillText(label, box.x + 6, Math.max(16, box.y - 7));
    ctx.restore();
  }

  function addRisk() {
    if (!currentImage) {
      setStatus("请先选择图片。", true);
      return;
    }
    var selected = riskTypeSelect.options[riskTypeSelect.selectedIndex];
    var riskName = selected ? selected.dataset.name : riskTypeSelect.value;
    var riskType = riskTypeSelect.value || riskName;
    var risk = {
      risk_type: riskType,
      risk_name: riskName || riskType,
      objects: splitList(riskObjectsInput.value),
      location: locationInput.value.trim(),
      bbox: toNormalizedBbox(currentBox),
      level: levelSelect.value,
      rule_id: selected ? selected.dataset.ruleId : "",
      reason: reasonInput.value.trim(),
      suggestion: suggestionInput.value.trim(),
    };
    risks.push(risk);
    currentBox = null;
    renderRiskList();
    redraw();
    setStatus("已添加风险标注。");
  }

  function renderRiskList() {
    if (risks.length === 0) {
      riskList.innerHTML = '<div class="empty-state">暂无风险标注。</div>';
      return;
    }
    riskList.innerHTML = "";
    risks.forEach(function (risk, index) {
      var row = document.createElement("div");
      row.className = "risk-row";
      row.innerHTML = '<div class="risk-row-head">' +
        '<strong>R' + (index + 1) + ' · ' + escapeHtml(risk.risk_name || risk.risk_type) + '</strong>' +
        '<button class="mini-btn" type="button">删除</button>' +
        '</div>' +
        '<p class="empty-state">' + escapeHtml(risk.level || "") + '风险 · ' +
        escapeHtml(risk.location || "未填写位置") + '</p>';
      row.querySelector("button").addEventListener("click", function () {
        risks.splice(index, 1);
        renderRiskList();
        redraw();
      });
      riskList.appendChild(row);
    });
  }

  function buildSample() {
    var sampleId = sanitizeId(sampleIdInput.value.trim());
    return {
      sample_id: sampleId,
      dataset: "custom",
      scene_type: sceneTypeSelect.value,
      title: titleInput.value.trim() || sampleId,
      summary: summaryInput.value.trim(),
      media: selectedFile ? [{
        type: "image",
        path: "datasets/custom/" + sampleId + getSuffix(selectedFile.name),
        view: "front",
        timestamp: null,
      }] : [],
      objects: splitList(objectsInput.value),
      regions: risks.map(function (risk) { return risk.location; }).filter(Boolean),
      ground_truth: risks,
      metadata: {
        source: "real_photo",
        license: "",
        created_at: new Date().toISOString().slice(0, 10),
      },
    };
  }

  function exportJson() {
    var sample = buildSample();
    if (!sample.sample_id) {
      setStatus("请填写样本 ID。", true);
      return;
    }
    var blob = new Blob([JSON.stringify([sample], null, 2)], { type: "application/json;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = sample.sample_id + "_annotations.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
    setStatus("已导出 JSON。");
  }

  function saveToDataset() {
    var sample = buildSample();
    if (!selectedFile) {
      setStatus("请先选择图片。", true);
      return;
    }
    if (!sample.sample_id) {
      setStatus("请填写样本 ID。", true);
      return;
    }
    var formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("sample_json", JSON.stringify(sample));
    saveBtn.disabled = true;
    setStatus("正在保存...");
    fetch(API_BASE + "/api/annotations/custom", {
      method: "POST",
      body: formData,
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.detail || "保存失败");
          return data;
        });
      })
      .then(function (data) {
        setStatus("已保存到 datasets/custom，风险数：" + data.risk_count);
      })
      .catch(function (err) {
        setStatus("保存失败：" + err.message, true);
      })
      .finally(function () {
        saveBtn.disabled = false;
      });
  }

  function splitList(value) {
    return value.split(/[,，、]/).map(function (item) {
      return item.trim();
    }).filter(Boolean);
  }

  function sanitizeId(value) {
    return value.replace(/[^\w-]/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "").slice(0, 80);
  }

  function getSuffix(filename) {
    var match = String(filename || "").match(/\.[^.]+$/);
    return match ? match[0].toLowerCase() : ".jpg";
  }

  function round4(value) {
    return Math.round(value * 10000) / 10000;
  }

  function setStatus(text, isError) {
    saveStatus.textContent = text;
    saveStatus.style.color = isError ? "var(--danger)" : "var(--muted)";
    drawStatus.textContent = text || "";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  init();
})();
