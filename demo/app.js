(function () {
  "use strict";

  var API_BASE = window.location.protocol === "file:" ? "http://localhost:8000" : "";
  var state = { providers: [], files: [], report: null, objectUrls: [] };

  var elements = {
    serviceState: document.getElementById("serviceState"),
    provider: document.getElementById("providerSelect"),
    prompt: document.getElementById("promptSelect"),
    apiKey: document.getElementById("apiKeyInput"),
    apiKeyHint: document.getElementById("apiKeyHint"),
    baseUrl: document.getElementById("baseUrlInput"),
    model: document.getElementById("modelInput"),
    temperature: document.getElementById("temperatureInput"),
    temperatureValue: document.getElementById("temperatureValue"),
    headers: document.getElementById("headersInput"),
    body: document.getElementById("bodyInput"),
    fileInput: document.getElementById("fileInput"),
    uploadZone: document.getElementById("uploadZone"),
    previewGrid: document.getElementById("previewGrid"),
    clearFiles: document.getElementById("clearFilesBtn"),
    inspect: document.getElementById("inspectBtn"),
    inspectText: document.getElementById("inspectBtnText"),
    spinner: document.getElementById("spinner"),
    error: document.getElementById("formError"),
    empty: document.getElementById("emptyState"),
    result: document.getElementById("reportResult"),
    meta: document.getElementById("resultMeta"),
    markdown: document.getElementById("markdownBody"),
    actions: document.getElementById("reportActions"),
    rulesDialog: document.getElementById("rulesDialog"),
    ruleList: document.getElementById("ruleList")
  };

  function requestJson(path) {
    return fetch(API_BASE + path).then(function (response) {
      if (!response.ok) throw new Error("服务响应异常（" + response.status + "）");
      return response.json();
    });
  }

  function setServiceState(ok, text) {
    elements.serviceState.classList.toggle("online", ok);
    elements.serviceState.classList.toggle("offline", !ok);
    elements.serviceState.lastChild.nodeValue = text;
  }

  function option(value, label) {
    var item = document.createElement("option");
    item.value = value;
    item.textContent = label;
    return item;
  }

  function loadConfiguration() {
    Promise.all([requestJson("/api/providers"), requestJson("/api/prompts"), requestJson("/api/risk_rules")])
      .then(function (responses) {
        var providerData = responses[0];
        state.providers = providerData.providers || [];
        elements.provider.replaceChildren();
        state.providers.forEach(function (provider) {
          elements.provider.appendChild(option(provider.name, provider.label || provider.name));
        });
        elements.prompt.replaceChildren();
        (responses[1].prompts || []).forEach(function (prompt) {
          elements.prompt.appendChild(option(prompt.id, prompt.id));
        });
        elements.provider.value = providerData.active || (state.providers[0] && state.providers[0].name) || "";
        syncProviderFields();
        renderRules(responses[2].rules || []);
        setServiceState(true, "API 服务已连接");
      })
      .catch(function (error) {
        setServiceState(false, "API 服务未连接");
        showError(error.message + "，请先运行 py -m src.server");
      });
  }

  function syncProviderFields() {
    var selected = state.providers.find(function (item) { return item.name === elements.provider.value; });
    if (!selected) return;
    elements.baseUrl.value = selected.base_url || "";
    elements.model.value = selected.model || "";
    if (selected.api_key_optional) {
      elements.apiKey.placeholder = "该服务无需 API Key";
      elements.apiKeyHint.textContent = "本地服务可留空";
    } else {
      elements.apiKey.placeholder = selected.has_env_key ? "已检测到环境变量，可留空" : "输入本次请求使用的 API Key";
      elements.apiKeyHint.textContent = (selected.api_key_env ? "环境变量：" + selected.api_key_env + "；" : "") + "不会保存到浏览器或服务器";
    }
    updateInspectState();
  }

  function addFiles(fileList) {
    var incoming = Array.from(fileList || []);
    incoming.forEach(function (file) {
      var duplicate = state.files.some(function (existing) {
        return existing.name === file.name && existing.size === file.size && existing.lastModified === file.lastModified;
      });
      if (!duplicate) state.files.push(file);
    });
    renderPreviews();
  }

  function clearFiles() {
    state.files = [];
    elements.fileInput.value = "";
    renderPreviews();
  }

  function removeFile(index) {
    state.files.splice(index, 1);
    renderPreviews();
  }

  function renderPreviews() {
    state.objectUrls.forEach(URL.revokeObjectURL);
    state.objectUrls = [];
    elements.previewGrid.replaceChildren();
    state.files.forEach(function (file, index) {
      var url = URL.createObjectURL(file);
      state.objectUrls.push(url);
      var item = document.createElement("div");
      item.className = "preview-item";
      var image = document.createElement("img");
      image.src = url;
      image.alt = file.name;
      var label = document.createElement("span");
      label.textContent = String(index + 1);
      var remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", "移除 " + file.name);
      remove.textContent = "×";
      remove.addEventListener("click", function () { removeFile(index); });
      item.append(image, label, remove);
      elements.previewGrid.appendChild(item);
    });
    elements.previewGrid.hidden = state.files.length === 0;
    elements.clearFiles.hidden = state.files.length === 0;
    elements.uploadZone.querySelector("strong").textContent = state.files.length ? "继续添加图片" : "添加图片";
    updateInspectState();
  }

  function updateInspectState() {
    elements.inspect.disabled = !state.files.length || !elements.provider.value || !elements.model.value.trim() || !elements.baseUrl.value.trim();
  }

  function showError(message) {
    elements.error.textContent = message;
    elements.error.hidden = !message;
  }

  function setLoading(loading) {
    elements.inspect.disabled = loading || !state.files.length;
    elements.inspectText.textContent = loading ? "模型分析中" : "开始巡检";
    elements.spinner.hidden = !loading;
  }

  function readError(response) {
    return response.json().then(function (data) { return data.detail || "请求失败"; }).catch(function () { return "请求失败"; });
  }

  function inspect() {
    showError("");
    var form = new FormData();
    state.files.forEach(function (file) { form.append("files", file, file.name); });
    form.append("provider_name", elements.provider.value);
    form.append("prompt_id", elements.prompt.value);
    form.append("api_key", elements.apiKey.value);
    form.append("base_url", elements.baseUrl.value.trim());
    form.append("model", elements.model.value.trim());
    form.append("temperature", elements.temperature.value);
    form.append("extra_headers", elements.headers.value.trim());
    form.append("extra_body", elements.body.value.trim());
    setLoading(true);
    fetch(API_BASE + "/api/inspect", { method: "POST", body: form })
      .then(function (response) {
        if (!response.ok) return readError(response).then(function (message) { throw new Error(message); });
        return response.json();
      })
      .then(renderResult)
      .catch(function (error) { showError(error.message); })
      .finally(function () { setLoading(false); updateInspectState(); });
  }

  function badge(text, className) {
    var item = document.createElement("span");
    item.className = "meta-badge " + className;
    item.textContent = text;
    return item;
  }

  function renderResult(payload) {
    state.report = payload.report;
    var inspection = payload.inspection || {};
    var data = inspection.data || {};
    elements.meta.replaceChildren();
    elements.meta.appendChild(badge(inspection.success ? "调用成功" : "调用失败", inspection.success ? "ok" : "danger"));
    if (inspection.success) {
      elements.meta.appendChild(badge(data.has_risk ? "发现风险 " + (data.risks || []).length + " 项" : "未发现风险", data.has_risk ? "warning" : "ok"));
      elements.meta.appendChild(badge(inspection.valid ? "格式通过" : "格式异常", inspection.valid ? "neutral" : "warning"));
    }
    elements.meta.appendChild(badge(inspection.model || inspection.provider, "neutral"));
    elements.markdown.innerHTML = payload.report.html;
    elements.empty.hidden = true;
    elements.result.hidden = false;
    elements.actions.hidden = false;
    elements.result.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function exportReport(format) {
    if (!state.report) return;
    var form = new FormData();
    form.append("content", state.report.markdown);
    form.append("format", format);
    form.append("filename", state.report.filename);
    fetch(API_BASE + "/api/reports/export", { method: "POST", body: form })
      .then(function (response) {
        if (!response.ok) return readError(response).then(function (message) { throw new Error(message); });
        return response.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = state.report.filename + "." + format;
        anchor.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      })
      .catch(function (error) { showError(error.message); });
  }

  function renderRules(rules) {
    elements.ruleList.replaceChildren();
    rules.forEach(function (rule) {
      var article = document.createElement("article");
      var title = document.createElement("h3");
      title.textContent = rule.risk_name;
      var id = document.createElement("code");
      id.textContent = rule.rule_id;
      var description = document.createElement("p");
      description.textContent = rule.description;
      var conditions = document.createElement("ul");
      (rule.trigger_conditions || []).forEach(function (condition) {
        var item = document.createElement("li");
        item.textContent = condition;
        conditions.appendChild(item);
      });
      article.append(title, id, description, conditions);
      elements.ruleList.appendChild(article);
    });
  }

  elements.uploadZone.addEventListener("click", function () { elements.fileInput.click(); });
  elements.fileInput.addEventListener("change", function () { addFiles(elements.fileInput.files); });
  elements.clearFiles.addEventListener("click", clearFiles);
  ["dragenter", "dragover"].forEach(function (eventName) {
    elements.uploadZone.addEventListener(eventName, function (event) { event.preventDefault(); elements.uploadZone.classList.add("dragging"); });
  });
  ["dragleave", "drop"].forEach(function (eventName) {
    elements.uploadZone.addEventListener(eventName, function (event) { event.preventDefault(); elements.uploadZone.classList.remove("dragging"); });
  });
  elements.uploadZone.addEventListener("drop", function (event) { addFiles(event.dataTransfer.files); });
  elements.provider.addEventListener("change", syncProviderFields);
  [elements.baseUrl, elements.model].forEach(function (input) { input.addEventListener("input", updateInspectState); });
  elements.temperature.addEventListener("input", function () { elements.temperatureValue.textContent = elements.temperature.value; });
  elements.inspect.addEventListener("click", inspect);
  document.querySelectorAll("[data-export]").forEach(function (button) {
    button.addEventListener("click", function () { exportReport(button.dataset.export); });
  });
  document.getElementById("rulesBtn").addEventListener("click", function () { elements.rulesDialog.showModal(); });
  document.getElementById("closeRulesBtn").addEventListener("click", function () { elements.rulesDialog.close(); });
  elements.rulesDialog.addEventListener("click", function (event) { if (event.target === elements.rulesDialog) elements.rulesDialog.close(); });

  loadConfiguration();
})();
