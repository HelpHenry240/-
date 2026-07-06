(function () {
  "use strict";

  // API 基础路径：同源时为空，独立打开时尝试连接本地后端
  var API_BASE = "";
  if (!window.location.pathname.includes("/demo/")) {
    API_BASE = "http://localhost:8000";
  } else if (window.location.port === "8000") {
    API_BASE = "";
  } else {
    API_BASE = "http://localhost:8000";
  }

  // DOM 元素
  var uploadZone = document.getElementById("uploadZone");
  var fileInput = document.getElementById("fileInput");
  var previewWrap = document.getElementById("previewWrap");
  var previewList = document.getElementById("previewList");
  var previewCount = document.getElementById("previewCount");
  var clearBtn = document.getElementById("clearBtn");
  var providerSelect = document.getElementById("providerSelect");
  var providerHint = document.getElementById("providerHint");
  var apiKeyGroup = document.getElementById("apiKeyGroup");
  var apiKeyInput = document.getElementById("apiKeyInput");
  var promptSelect = document.getElementById("promptSelect");
  var mockSceneGroup = document.getElementById("mockSceneGroup");
  var mockSceneSelect = document.getElementById("mockSceneSelect");
  var inspectBtn = document.getElementById("inspectBtn");
  var loadingBar = document.getElementById("loadingBar");
  var resultEmpty = document.getElementById("resultEmpty");
  var resultContent = document.getElementById("resultContent");
  var statusBadge = document.getElementById("statusBadge");
  var validBadge = document.getElementById("validBadge");
  var metaProvider = document.getElementById("metaProvider");
  var metaModel = document.getElementById("metaModel");
  var metaInput = document.getElementById("metaInput");
  var metaTime = document.getElementById("metaTime");
  var riskList = document.getElementById("riskList");
  var evidenceBox = document.getElementById("evidenceBox");
  var jsonOutput = document.getElementById("jsonOutput");
  var rawOutput = document.getElementById("rawOutput");
  var errorBox = document.getElementById("errorBox");
  var heatmapBox = document.getElementById("heatmapBox");

  var selectedFiles = [];
  var nextFileId = 1;

  // ===== 初始化：加载 providers 和 prompts =====
  function init() {
    loadProviders();
    loadPrompts();
    loadMockScenes();
    setupEventListeners();
  }

  function loadProviders() {
    fetch(API_BASE + "/api/providers")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        providerSelect.innerHTML = "";
        (data.providers || []).forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = p.name;
          var label = p.name;
          if (p.model) label += " (" + p.model + ")";
          if (!p.has_env_key && p.api_key_env) label += " [需输入 Key]";
          opt.textContent = label;
          providerSelect.appendChild(opt);
        });
        if (data.active) providerSelect.value = data.active;
        onProviderChange();
      })
      .catch(function () {
        // 后端未启动时，只保留 mock 选项
        providerSelect.innerHTML = '<option value="mock">Mock（后端未连接，仅本地模拟）</option>';
        onProviderChange();
      });
  }

  function loadPrompts() {
    fetch(API_BASE + "/api/prompts")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var prompts = data.prompts || [];
        if (prompts.length === 0) return;
        promptSelect.innerHTML = "";
        prompts.forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = p.name;
          promptSelect.appendChild(opt);
        });
      })
      .catch(function () {});
  }

  function loadMockScenes() {
    var scenes = window.DEMO_SCENES || [];
    scenes.forEach(function (s) {
      var opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.id + " " + s.title;
      mockSceneSelect.appendChild(opt);
    });
  }

  // ===== 事件绑定 =====
  function setupEventListeners() {
    uploadZone.addEventListener("click", function () { fileInput.click(); });
    fileInput.addEventListener("change", onFileChange);
    uploadZone.addEventListener("dragover", function (e) {
      e.preventDefault();
      uploadZone.classList.add("dragover");
    });
    uploadZone.addEventListener("dragleave", function () {
      uploadZone.classList.remove("dragover");
    });
    uploadZone.addEventListener("drop", function (e) {
      e.preventDefault();
      uploadZone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    });
    clearBtn.addEventListener("click", clearFile);
    providerSelect.addEventListener("change", onProviderChange);
    inspectBtn.addEventListener("click", doInspect);

    // Tab 切换
    document.querySelectorAll(".tab-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tab = btn.dataset.tab;
        document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.remove("active"); });
        document.querySelectorAll(".tab-content").forEach(function (c) { c.classList.remove("active"); });
        btn.classList.add("active");
        document.getElementById("tab" + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add("active");
      });
    });
  }

  function onFileChange(e) {
    if (e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  }

  function handleFiles(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    if (files.length === 0) return;

    processFileQueue(files, 0);
  }

  function processFileQueue(files, index) {
    if (index >= files.length) {
      fileInput.value = "";
      renderPreviews();
      return;
    }

    buildSelectedFile(files[index], function (item) {
      if (item) selectedFiles.push(item);
      processFileQueue(files, index + 1);
    });
  }

  function buildSelectedFile(file, callback) {
    var lowerName = (file.name || "").toLowerCase();
    var isSvg = file.type === "image/svg+xml" || lowerName.endsWith(".svg");
    var isImage = file.type.startsWith("image/") || isSvg;

    if (!isImage) {
      alert("已跳过非图片文件：" + file.name);
      callback(null);
      return;
    }

    // SVG 文件需要先转成 PNG，因为 Qwen-VL 等模型不支持 SVG 格式
    if (isSvg) {
      convertSvgToPng(file, function (pngFile) {
        callback(createSelectedFile(pngFile || file, file));
      });
    } else {
      callback(createSelectedFile(file, file));
    }
  }

  function createSelectedFile(uploadFile, previewFile) {
    return {
      id: nextFileId++,
      uploadFile: uploadFile,
      previewName: previewFile.name || uploadFile.name || "未命名图片",
      previewUrl: URL.createObjectURL(previewFile),
    };
  }

  function renderPreviews() {
    previewList.innerHTML = "";

    selectedFiles.forEach(function (item, index) {
      var card = document.createElement("div");
      card.className = "preview-item";

      var img = document.createElement("img");
      img.src = item.previewUrl;
      img.alt = "视角 " + (index + 1);

      var name = document.createElement("div");
      name.className = "preview-name";
      name.textContent = "视角 " + (index + 1) + " · " + item.previewName;

      var removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "preview-clear";
      removeBtn.textContent = "×";
      removeBtn.title = "移除这张图片";
      removeBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        removeFile(item.id);
      });

      card.appendChild(img);
      card.appendChild(name);
      card.appendChild(removeBtn);
      previewList.appendChild(card);
    });

    previewWrap.style.display = selectedFiles.length > 0 ? "block" : "none";
    previewCount.textContent = "已选择 " + selectedFiles.length + " 张图片";
    inspectBtn.disabled = selectedFiles.length === 0;
  }

  function removeFile(id) {
    selectedFiles = selectedFiles.filter(function (item) {
      if (item.id === id) {
        URL.revokeObjectURL(item.previewUrl);
        return false;
      }
      return true;
    });
    renderPreviews();
  }

  function convertSvgToPng(svgFile, callback) {
    var reader = new FileReader();
    reader.onload = function (e) {
      var svgText = e.target.result;
      var img = new Image();
      img.onload = function () {
        // 用 canvas 渲染 SVG 并导出为 PNG
        var canvas = document.createElement("canvas");
        canvas.width = img.width || 640;
        canvas.height = img.height || 430;
        var ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(function (blob) {
          if (blob) {
            // 保留原文件名，扩展名改为 .png
            var pngName = svgFile.name.replace(/\.svg$/i, ".png");
            var pngFile = new File([blob], pngName, { type: "image/png" });
            console.log("SVG converted to PNG:", pngName, pngFile.size, "bytes");
            callback(pngFile);
          } else {
            console.error("SVG to PNG conversion failed: toBlob returned null");
            callback(null);
          }
        }, "image/png");
      };
      img.onerror = function () {
        console.error("SVG to PNG conversion failed: image load error");
        callback(null);
      };
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgText);
    };
    reader.onerror = function () {
      console.error("SVG file read error");
      callback(null);
    };
    reader.readAsText(svgFile);
  }

  function clearFile() {
    selectedFiles.forEach(function (item) {
      URL.revokeObjectURL(item.previewUrl);
    });
    selectedFiles = [];
    fileInput.value = "";
    renderPreviews();
  }

  function onProviderChange() {
    var providerName = providerSelect.value;
    var selectedOption = providerSelect.options[providerSelect.selectedIndex];
    var text = selectedOption ? selectedOption.textContent : "";

    if (providerName === "mock") {
      apiKeyGroup.style.display = "none";
      mockSceneGroup.style.display = "block";
      providerHint.textContent = "本地模拟，无需网络和 API Key。";
    } else {
      apiKeyGroup.style.display = "block";
      mockSceneGroup.style.display = "none";
      if (text.includes("[需输入 Key]")) {
        providerHint.textContent = "环境变量未设置，请在下方输入 API Key。";
      } else {
        providerHint.textContent = "环境变量已配置，可直接使用或输入 Key 覆盖。";
      }
    }
  }

  // ===== 执行巡检 =====
  function doInspect() {
    if (selectedFiles.length === 0) return;

    var providerName = providerSelect.value;
    var apiKey = apiKeyInput.value.trim();
    var promptId = promptSelect.value;
    var mockScene = mockSceneSelect.value;

    // 显示加载状态
    inspectBtn.disabled = true;
    inspectBtn.textContent = "巡检中...";
    loadingBar.classList.add("active");
    resultEmpty.style.display = "none";
    resultContent.style.display = "block";
    errorBox.style.display = "none";

    var formData = new FormData();
    selectedFiles.forEach(function (item) {
      formData.append("files", item.uploadFile);
    });
    formData.append("provider_name", providerName);
    if (apiKey) formData.append("api_key", apiKey);
    formData.append("prompt_id", promptId);
    if (mockScene) formData.append("mock_scene", mockScene);

    fetch(API_BASE + "/api/inspect", {
      method: "POST",
      body: formData,
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        renderResult(data, providerName);
      })
      .catch(function (err) {
        showError("请求失败：" + err.message + "\n\n请确认后端服务已启动：python -m src.server");
      })
      .finally(function () {
        inspectBtn.disabled = false;
        inspectBtn.textContent = "开始巡检";
        loadingBar.classList.remove("active");
      });
  }

  // ===== 渲染结果 =====
  function renderResult(data, providerName) {
    var model = data.model || "";
    var timestamp = data.timestamp || "";
    var success = data.success;

    // 元信息
    metaProvider.textContent = "Provider: " + (data.provider || providerName);
    metaModel.textContent = model ? "Model: " + model : "";
    metaInput.textContent = data.input_count ? "Images: " + data.input_count : "";
    metaTime.textContent = timestamp ? "Time: " + timestamp : "";

    // 状态 badge
    if (success) {
      statusBadge.textContent = "调用成功";
      statusBadge.className = "badge ok";
    } else {
      statusBadge.textContent = "调用失败";
      statusBadge.className = "badge risk";
    }

    // 校验 badge
    if (data.valid !== undefined) {
      if (data.valid) {
        validBadge.textContent = "格式校验通过";
        validBadge.className = "badge ok";
      } else {
        validBadge.textContent = "格式校验失败";
        validBadge.className = "badge partial";
      }
    } else {
      validBadge.textContent = "";
      validBadge.className = "badge";
      validBadge.style.display = "none";
    }

    // JSON 输出
    jsonOutput.textContent = JSON.stringify(data.data || data, null, 2);

    // 原文输出
    rawOutput.textContent = data.raw_text || "(无原文输出)";

    if (!success) {
      showError(data.error || "调用失败，请检查 API Key 和网络连接。");
      renderHeatmap([]);
      riskList.innerHTML = "";
      evidenceBox.innerHTML = "";
      return;
    }

    // 可视化风险列表
    var riskData = data.data || {};
    var risks = riskData.risks || [];
    renderHeatmap(risks);

    if (!riskData.has_risk || risks.length === 0) {
      riskList.innerHTML = '<div class="result-box"><h3>巡检结果</h3><p class="empty-state">未发现风险。</p></div>';
    } else {
      riskList.innerHTML = risks.map(function (risk, i) {
        var levelClass = risk.level === "高" ? "risk" : risk.level === "中" ? "partial" : "ok";
        return '<div class="result-risk-item">' +
          '<div class="badge-row">' +
          '<span class="badge risk">' + escapeHtml(risk.type || "未知风险") + '</span>' +
          '<span class="badge ' + levelClass + '">' + escapeHtml(risk.level || "") + '风险</span>' +
          '</div>' +
          '<p><strong>相关物体：</strong>' + escapeHtml((risk.objects || []).join("、")) + '</p>' +
          '<p><strong>位置：</strong>' + escapeHtml(risk.location || "") + '</p>' +
          '<p><strong>依据：</strong>' + escapeHtml(risk.reason || "") + '</p>' +
          '<p><strong>建议：</strong>' + escapeHtml(risk.suggestion || "") + '</p>' +
          '</div>';
      }).join("");
    }

    // 证据充分性
    var evidence = riskData.evidence_sufficiency || "";
    var uncertain = riskData.uncertain_points || [];
    var evidenceHtml = "<h3>证据与不确定性</h3>";
    if (evidence) {
      evidenceHtml += '<p><strong>证据充分性：</strong>' + escapeHtml(evidence) + '</p>';
    }
    if (uncertain.length > 0) {
      evidenceHtml += '<p><strong>不确定点：</strong>' + uncertain.map(escapeHtml).join("；") + '</p>';
    }
    if (!evidence && uncertain.length === 0) {
      evidenceHtml += '<p class="empty-state">模型未报告证据充分性信息。</p>';
    }
    evidenceBox.innerHTML = evidenceHtml;

    // 校验错误
    if (data.validation_error) {
      errorBox.style.display = "block";
      errorBox.textContent = "格式校验警告：" + data.validation_error;
    }
  }

  function renderHeatmap(risks) {
    var boxedRisks = (risks || []).filter(function (risk) {
      return getRiskBbox(risk) !== null;
    });
    if (!heatmapBox || boxedRisks.length === 0 || selectedFiles.length === 0) {
      if (heatmapBox) {
        heatmapBox.style.display = "none";
        heatmapBox.innerHTML = "";
      }
      return;
    }

    var stage = document.createElement("div");
    stage.className = "heatmap-stage";

    var img = document.createElement("img");
    img.src = selectedFiles[0].previewUrl;
    img.alt = "风险热区";
    stage.appendChild(img);

    boxedRisks.forEach(function (risk, index) {
      var bbox = normalizeBboxForCss(getRiskBbox(risk));
      if (!bbox) return;

      var region = document.createElement("div");
      region.className = "heatmap-region";
      region.style.left = bbox[0] + "%";
      region.style.top = bbox[1] + "%";
      region.style.width = bbox[2] + "%";
      region.style.height = bbox[3] + "%";

      var label = document.createElement("div");
      label.className = "heatmap-label";
      label.textContent = "R" + (index + 1) + " " + (risk.type || risk.risk_name || "风险");
      region.appendChild(label);
      stage.appendChild(region);
    });

    heatmapBox.innerHTML = "<h3>风险热区</h3>";
    heatmapBox.appendChild(stage);
    heatmapBox.style.display = "block";
  }

  function getRiskBbox(risk) {
    var candidates = [risk && risk.bbox, risk && risk.region_bbox, risk && risk.bounding_box];
    for (var i = 0; i < candidates.length; i += 1) {
      var bbox = candidates[i];
      if (Array.isArray(bbox) && bbox.length >= 4) return bbox.slice(0, 4).map(Number);
      if (bbox && typeof bbox === "object") {
        var values = [bbox.x, bbox.y, bbox.width || bbox.w, bbox.height || bbox.h].map(Number);
        if (values.every(function (v) { return Number.isFinite(v); })) return values;
      }
    }
    return null;
  }

  function normalizeBboxForCss(bbox) {
    if (!bbox || bbox.some(function (v) { return !Number.isFinite(v); })) return null;
    var maxVal = Math.max.apply(null, bbox.map(Math.abs));
    var scale = maxVal <= 1 ? 100 : 1;
    var x = bbox[0] * scale;
    var y = bbox[1] * scale;
    var w = bbox[2] * scale;
    var h = bbox[3] * scale;
    if (w <= 0 || h <= 0) return null;
    x = clamp(x, 0, 100);
    y = clamp(y, 0, 100);
    w = clamp(w, 0, 100 - x);
    h = clamp(h, 0, 100 - y);
    return [x, y, w, h];
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function showError(msg) {
    errorBox.style.display = "block";
    errorBox.textContent = msg;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // 启动
  if (window.DEMO_SCENES === undefined) {
    // inspect.html 独立打开时可能没有 data.js，加载一个空的
    window.DEMO_SCENES = [];
  }
  init();
})();
