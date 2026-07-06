(function () {
  "use strict";

  var API_BASE = "";
  if (!window.location.pathname.includes("/demo/")) {
    API_BASE = "http://localhost:8000";
  } else if (window.location.port === "8000") {
    API_BASE = "";
  } else {
    API_BASE = "http://localhost:8000";
  }

  // DOM
  var datasetSelect = document.getElementById("datasetSelect");
  var datasetHint = document.getElementById("datasetHint");
  var providerSelect = document.getElementById("providerSelect");
  var promptSelect = document.getElementById("promptSelect");
  var apiKeyGroup = document.getElementById("apiKeyGroup");
  var apiKeyInput = document.getElementById("apiKeyInput");
  var runBtn = document.getElementById("runBtn");
  var loadingOverlay = document.getElementById("loadingOverlay");
  var loadingProgress = document.getElementById("loadingProgress");
  var resultSection = document.getElementById("resultSection");
  var runIdLabel = document.getElementById("runIdLabel");
  var statsGrid = document.getElementById("statsGrid");
  var sampleTableBody = document.getElementById("sampleTableBody");
  var failureList = document.getElementById("failureList");
  var historyTableBody = document.getElementById("historyTableBody");

  function init() {
    loadDatasets();
    loadProviders();
    loadPrompts();
    loadHistory();
    setupTabs();
    runBtn.addEventListener("click", runBatch);
    providerSelect.addEventListener("change", onProviderChange);
  }

  function loadDatasets() {
    fetch(API_BASE + "/api/datasets")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var datasets = data.datasets || [];
        if (datasets.length <= 1) return;
        datasetSelect.innerHTML = "";
        datasets.forEach(function (d) {
          var opt = document.createElement("option");
          opt.value = d.name;
          opt.textContent = d.name + " (" + d.sample_count + " 张)";
          datasetSelect.appendChild(opt);
        });
        updateDatasetHint(datasets);
      })
      .catch(function () {});
  }

  function updateDatasetHint(datasets) {
    var selected = datasets.find(function (d) { return d.name === datasetSelect.value; });
    if (selected) {
      var hint = selected.sample_count + " 个样本";
      if (selected.has_annotations) hint += "，有标注";
      datasetHint.textContent = hint;
    }
  }

  function loadProviders() {
    fetch(API_BASE + "/api/providers")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        providerSelect.innerHTML = "";
        (data.providers || []).forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = p.name;
          opt.textContent = p.name + (p.model ? " (" + p.model + ")" : "");
          providerSelect.appendChild(opt);
        });
        if (data.active) providerSelect.value = data.active;
        onProviderChange();
      })
      .catch(function () {});
  }

  function loadPrompts() {
    fetch(API_BASE + "/api/prompts")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var prompts = data.prompts || [];
        if (prompts.length <= 1) return;
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

  function onProviderChange() {
    var name = providerSelect.value;
    if (name === "mock") {
      apiKeyGroup.style.display = "none";
    } else {
      apiKeyGroup.style.display = "grid";
    }
  }

  function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tab = btn.dataset.tab;
        document.querySelectorAll(".tab-btn").forEach(function (b) { b.classList.remove("active"); });
        document.querySelectorAll(".tab-content").forEach(function (c) { c.classList.remove("active"); });
        btn.classList.add("active");
        var tabId = "tab" + tab.charAt(0).toUpperCase() + tab.slice(1);
        var el = document.getElementById(tabId);
        if (el) el.classList.add("active");
      });
    });
  }

  function runBatch() {
    var dataset = datasetSelect.value;
    var providerName = providerSelect.value;
    var apiKey = apiKeyInput.value.trim();
    var promptId = promptSelect.value;

    runBtn.disabled = true;
    runBtn.textContent = "运行中...";
    loadingOverlay.classList.add("active");
    resultSection.style.display = "none";
    loadingProgress.textContent = "数据集: " + dataset + " | Provider: " + providerName;

    var formData = new FormData();
    formData.append("dataset", dataset);
    formData.append("provider_name", providerName);
    if (apiKey) formData.append("api_key", apiKey);
    formData.append("prompt_id", promptId);

    fetch(API_BASE + "/api/run_batch", { method: "POST", body: formData })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        renderResult(data);
        loadHistory();
      })
      .catch(function (err) {
        alert("批量运行失败: " + err.message + "\n请确认后端服务已启动");
      })
      .finally(function () {
        runBtn.disabled = false;
        runBtn.textContent = "开始批量运行";
        loadingOverlay.classList.remove("active");
      });
  }

  function renderResult(data) {
    resultSection.style.display = "block";
    var run = data.run || {};
    var evalData = data.evaluation || {};
    var runId = run.run_id || "";
    runIdLabel.textContent = runId;

    // 统计卡片
    var total = evalData.total_samples || 0;
    var correct = evalData.correct_samples || 0;
    var accuracy = evalData.accuracy || 0;
    var miss = evalData.miss_count || 0;
    var falseAlarm = evalData.false_alarm_count || 0;
    var levelErr = evalData.level_error_count || 0;
    var riskSamples = evalData.risk_samples || 0;
    var normalSamples = evalData.normal_samples || 0;

    statsGrid.innerHTML = [
      statCard("准确率", (accuracy * 100).toFixed(1) + "%", "success"),
      statCard("正确", correct + "/" + total, "success"),
      statCard("漏检", miss, "danger"),
      statCard("误检", falseAlarm, "danger"),
      statCard("等级错误", levelErr, "warning"),
      statCard("风险样本", riskSamples, ""),
      statCard("正常样本", normalSamples, ""),
      statCard("类别覆盖", (evalData.risk_category_detected || 0) + "/" + (evalData.risk_category_coverage || 0), ""),
    ].join("");

    // 样本明细
    var sampleEvals = data.sample_evaluations || [];
    sampleTableBody.innerHTML = sampleEvals.map(function (s) {
      var resultBadge = s.is_correct
        ? '<span class="badge ok">正确</span>'
        : '<span class="badge risk">错误</span>';
      var gtTypes = (s.errors || []).map(function(e) { return e.error_type; }).join(", ");
      var gtText = s.gt_risk_count > 0 ? s.gt_risk_count + " 个风险" : "无风险";
      var modelText = s.model_risk_count > 0 ? s.model_risk_count + " 个风险" : "无风险";
      return '<tr>' +
        '<td><strong>' + escapeHtml(s.sample_id) + '</strong><br><span style="color:var(--muted);font-size:12px;">' + escapeHtml(s.title) + '</span></td>' +
        '<td>' + escapeHtml(s.scene_type || "") + '</td>' +
        '<td>' + gtText + '</td>' +
        '<td>' + modelText + '</td>' +
        '<td>' + resultBadge + (gtTypes ? '<br><span style="color:var(--muted);font-size:12px;">' + escapeHtml(gtTypes) + '</span>' : '') + '</td>' +
        '</tr>';
    }).join("");

    // 失败案例
    var failures = data.failure_cases || [];
    if (failures.length === 0) {
      failureList.innerHTML = '<div class="empty-state">没有失败案例，全部正确！</div>';
    } else {
      failureList.innerHTML = failures.map(function (f) {
        var errors = f.errors || [];
        var errorHtml = errors.map(function (err) {
          var causes = (err.possible_causes || []).map(function(c) { return "<li>" + escapeHtml(c) + "</li>"; }).join("");
          var improvements = (err.improvements || []).map(function(i) { return "<li>" + escapeHtml(i) + "</li>"; }).join("");
          return '<div class="error-detail">' +
            '<span class="badge risk">' + escapeHtml(err.error_type) + '</span> ' +
            escapeHtml(err.detail || "") +
            (causes ? '<div class="analysis-section"><h4>可能原因</h4><ul>' + causes + '</ul></div>' : '') +
            (improvements ? '<div class="analysis-section"><h4>改进方案</h4><ul>' + improvements + '</ul></div>' : '') +
            '</div>';
        }).join("");

        var gtHtml = (f.ground_truth || []).map(function(g) {
          return escapeHtml(g.type || g.risk_type || "") + " (" + escapeHtml(g.level || "") + ")";
        }).join(", ") || "无风险";
        var modelHtml = (f.model_output && f.model_output.risks) ? (f.model_output.risks || []).map(function(r) {
          return escapeHtml(r.type || "") + " (" + escapeHtml(r.level || "") + ")";
        }).join(", ") : "无风险";

        return '<div class="failure-card">' +
          '<div class="badge-row">' +
          '<span class="badge risk">' + escapeHtml(f.sample_id) + '</span>' +
          '<span style="color:var(--muted);font-size:13px;">' + escapeHtml(f.title || "") + ' | ' + escapeHtml(f.scene_type || "") + '</span>' +
          '</div>' +
          '<p style="margin:8px 0;font-size:13px;"><strong>人工标注:</strong> ' + gtHtml + '</p>' +
          '<p style="margin:8px 0;font-size:13px;"><strong>模型输出:</strong> ' + modelHtml + '</p>' +
          errorHtml +
          '</div>';
      }).join("");
    }
  }

  function loadHistory() {
    fetch(API_BASE + "/api/runs")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var runs = data.runs || [];
        if (runs.length === 0) {
          historyTableBody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无历史运行记录</td></tr>';
          return;
        }
        historyTableBody.innerHTML = runs.map(function (r) {
          var s = r.summary || {};
          return '<tr>' +
            '<td><strong>' + escapeHtml(r.run_id) + '</strong></td>' +
            '<td>' + escapeHtml(r.dataset) + '</td>' +
            '<td>' + escapeHtml(r.provider) + '</td>' +
            '<td>' + (s.success || 0) + '/' + (s.total || 0) + '</td>' +
            '<td>' + escapeHtml(r.created_at || "") + '</td>' +
            '</tr>';
        }).join("");
      })
      .catch(function () {
        historyTableBody.innerHTML = '<tr><td colspan="5" class="empty-state">无法加载历史记录</td></tr>';
      });
  }

  function statCard(label, value, modifier) {
    return '<div class="stat-card ' + (modifier || "") + '">' +
      '<div class="stat-value">' + escapeHtml(value) + '</div>' +
      '<div class="stat-label">' + escapeHtml(label) + '</div>' +
      '</div>';
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
