(function () {
  "use strict";

  var API_BASE = "";
  if (window.location.port === "8000") {
    API_BASE = "";
  } else {
    API_BASE = "http://localhost:8000";
  }

  var datasetSelect = document.getElementById("datasetSelect");
  var providerSelect = document.getElementById("providerSelect");
  var apiKeyGroup = document.getElementById("apiKeyGroup");
  var apiKeyInput = document.getElementById("apiKeyInput");
  var promptCheckboxRow = document.getElementById("promptCheckboxRow");
  var runCompareBtn = document.getElementById("runCompareBtn");
  var loadingOverlay = document.getElementById("loadingOverlay");
  var loadingText = document.getElementById("loadingText");
  var resultSection = document.getElementById("resultSection");
  var summaryBox = document.getElementById("summaryBox");
  var metricsTable = document.getElementById("metricsTable");
  var sampleCompareTable = document.getElementById("sampleCompareTable");
  var divergentSection = document.getElementById("divergentSection");
  var divergentList = document.getElementById("divergentList");

  var selectedPrompts = new Set();

  function init() {
    loadProviders();
    loadPrompts();
    providerSelect.addEventListener("change", onProviderChange);
    runCompareBtn.addEventListener("click", runCompare);
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
        promptCheckboxRow.innerHTML = "";
        prompts.forEach(function (p) {
          var label = document.createElement("label");
          var checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.value = p.id;
          checkbox.addEventListener("change", function () {
            if (checkbox.checked) {
              selectedPrompts.add(p.id);
              label.classList.add("checked");
            } else {
              selectedPrompts.delete(p.id);
              label.classList.remove("checked");
            }
          });
          label.appendChild(checkbox);
          label.appendChild(document.createTextNode(p.name));
          promptCheckboxRow.appendChild(label);
        });
      })
      .catch(function () {});
  }

  function onProviderChange() {
    var name = providerSelect.value;
    apiKeyGroup.style.display = (name === "mock") ? "none" : "grid";
  }

  function runCompare() {
    var prompts = Array.from(selectedPrompts);
    if (prompts.length < 2) {
      alert("请至少选择 2 个 Prompt 模板进行对比");
      return;
    }

    var dataset = datasetSelect.value;
    var providerName = providerSelect.value;
    var apiKey = apiKeyInput.value.trim();

    runCompareBtn.disabled = true;
    runCompareBtn.textContent = "对比中...";
    loadingOverlay.classList.add("active");
    resultSection.style.display = "none";
    loadingText.textContent = "正在用 " + prompts.length + " 个 Prompt 分别运行 " + dataset + " 数据集...";

    var formData = new FormData();
    formData.append("dataset", dataset);
    formData.append("provider_name", providerName);
    if (apiKey) formData.append("api_key", apiKey);
    formData.append("prompt_ids", prompts.join(","));

    fetch(API_BASE + "/api/run_multi_batch", { method: "POST", body: formData })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        renderResult(data);
      })
      .catch(function (err) {
        alert("对比运行失败: " + err.message + "\n请确认后端服务已启动");
      })
      .finally(function () {
        runCompareBtn.disabled = false;
        runCompareBtn.textContent = "运行对比";
        loadingOverlay.classList.remove("active");
      });
  }

  function renderResult(data) {
    resultSection.style.display = "block";
    var comparison = data.comparison || {};
    var runs = comparison.runs || [];
    var summary = comparison.summary || {};

    // 摘要
    var summaryHtml = "";
    if (summary.best_run_id) {
      summaryHtml += "<strong>最佳 Prompt:</strong> " + escapeHtml(summary.best_run_id) +
        "，准确率 " + ((summary.best_accuracy || 0) * 100).toFixed(1) + "%<br>";
    }
    if (summary.comparison_type === "prompt") {
      summaryHtml += "<strong>对比类型:</strong> 多 Prompt 对比<br>";
    }
    if (summary.prompts_compared) {
      summaryHtml += "<strong>对比的 Prompt:</strong> " + escapeHtml(summary.prompts_compared.join(", "));
    }
    summaryBox.innerHTML = summaryHtml || "对比完成。";

    // 指标对比表
    var metrics = [
      { key: "accuracy", label: "准确率", format: function(v) { return (v * 100).toFixed(1) + "%"; }, higher: true },
      { key: "correct_samples", label: "正确数", format: function(v) { return v; }, higher: true },
      { key: "miss_count", label: "漏检数", format: function(v) { return v; }, higher: false },
      { key: "false_alarm_count", label: "误检数", format: function(v) { return v; }, higher: false },
      { key: "level_error_count", label: "等级错误", format: function(v) { return v; }, higher: false },
      { key: "risk_category_detected", label: "类别检出", format: function(v) { return v; }, higher: true },
    ];

    // 找每行最佳值
    var headerHtml = "<tr><th>指标</th>";
    runs.forEach(function (r) {
      headerHtml += "<th>" + escapeHtml(r.prompt_id || r.run_id) + "</th>";
    });
    headerHtml += "</tr>";

    var bodyHtml = "";
    metrics.forEach(function (m) {
      var values = runs.map(function (r) { return (r.metrics || {})[m.key] || 0; });
      var bestVal = m.higher ? Math.max.apply(null, values) : Math.min.apply(null, values);

      var rowHtml = "<tr><td>" + escapeHtml(m.label) + "</td>";
      values.forEach(function (v) {
        var formatted = m.format(v);
        var isBest = v === bestVal;
        rowHtml += '<td class="' + (isBest ? "best" : "") + '">' + escapeHtml(formatted) + "</td>";
      });
      rowHtml += "</tr>";
      bodyHtml += rowHtml;
    });

    metricsTable.innerHTML = headerHtml + bodyHtml;

    // 逐样本对比表
    var sampleComparison = comparison.sample_comparison || [];
    var sampleHeader = "<tr><th>样本</th>";
    runs.forEach(function (r) {
      sampleHeader += "<th>" + escapeHtml(r.prompt_id || r.run_id) + "</th>";
    });
    sampleHeader += "</tr>";

    var sampleBody = "";
    sampleComparison.forEach(function (s) {
      var rowHtml = "<tr><td><strong>" + escapeHtml(s.sample_id) + "</strong><br><span style='color:var(--muted);font-size:11px;'>" + escapeHtml(s.title || "") + "</span></td>";
      (s.results || []).forEach(function (r) {
        if (r.is_correct === true) {
          rowHtml += '<td><span class="badge ok">正确</span></td>';
        } else if (r.is_correct === false) {
          var errs = (r.errors || []).join(", ");
          rowHtml += '<td><span class="badge risk">错误</span><br><span style="font-size:11px;color:var(--muted);">' + escapeHtml(errs) + "</span></td>";
        } else {
          rowHtml += '<td><span class="badge partial">-</span></td>';
        }
      });
      rowHtml += "</tr>";
      sampleBody += rowHtml;
    });
    sampleCompareTable.innerHTML = sampleHeader + sampleBody;

    // 差异样本
    var divergent = comparison.divergent_samples || [];
    if (divergent.length > 0) {
      divergentSection.style.display = "block";
      divergentList.innerHTML = divergent.map(function (s) {
        var results = s.results || [];
        var resultsHtml = results.map(function (r, i) {
          var status = r.is_correct ? '<span class="badge ok">正确</span>' : '<span class="badge risk">错误</span>';
          var errs = (r.errors || []).join(", ");
          return '<strong>' + escapeHtml(runs[i] ? runs[i].prompt_id : "") + ":</strong> " + status + (errs ? " (" + escapeHtml(errs) + ")" : "");
        }).join(" | ");
        return '<div style="padding:10px;border:1px solid var(--line);border-radius:6px;margin-bottom:8px;">' +
          "<strong>" + escapeHtml(s.sample_id) + "</strong> " + escapeHtml(s.title || "") + "<br>" +
          resultsHtml + "</div>";
      }).join("");
    } else {
      divergentSection.style.display = "none";
    }
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
