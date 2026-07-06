(function () {
  const scenes = window.DEMO_SCENES || [];
  const rules = window.RISK_RULES || [];
  const modelResults = window.MOCK_RESULTS || {};

  const sceneList = document.getElementById("sceneList");
  const detailPanel = document.getElementById("detailPanel");
  const summaryGrid = document.getElementById("summaryGrid");
  const rulesGrid = document.getElementById("rulesGrid");
  const failureGrid = document.getElementById("failureGrid");
  const filter = document.getElementById("sceneFilter");
  const exportButton = document.getElementById("exportReport");

  let currentSceneId = scenes[0]?.id;

  function riskTypes(risks) {
    return new Set((risks || []).map((risk) => risk.type));
  }

  function compare(scene) {
    const truth = scene.ground_truth || [];
    const predicted = modelResults[scene.id]?.risks || [];
    const truthSet = riskTypes(truth);
    const predictedSet = riskTypes(predicted);
    const missed = truth.filter((risk) => !predictedSet.has(risk.type));
    const falsePositive = predicted.filter((risk) => !truthSet.has(risk.type));
    const matched = predicted.filter((risk) => truthSet.has(risk.type));
    const levelMismatch = matched.filter((risk) => {
      const expected = truth.find((item) => item.type === risk.type);
      return expected && expected.level !== risk.level;
    });

    let status = "correct";
    if (missed.length || falsePositive.length) status = "failure";
    else if (levelMismatch.length) status = "partial";

    return { truth, predicted, missed, falsePositive, matched, levelMismatch, status };
  }

  function statusBadge(status) {
    if (status === "correct") return '<span class="badge ok">识别正确</span>';
    if (status === "partial") return '<span class="badge partial">部分正确</span>';
    return '<span class="badge risk">失败案例</span>';
  }

  function riskBadge(scene) {
    return (scene.ground_truth || []).length
      ? '<span class="badge risk">人工标注: 有风险</span>'
      : '<span class="badge ok">人工标注: 正常</span>';
  }

  function filteredScenes() {
    const value = filter.value;
    return scenes.filter((scene) => {
      const itemCompare = compare(scene);
      const hasTruthRisk = (scene.ground_truth || []).length > 0;
      if (value === "all") return true;
      if (value === "risk") return hasTruthRisk;
      if (value === "normal") return !hasTruthRisk;
      if (value === "failure") return itemCompare.status === "failure" || itemCompare.status === "partial";
      return scene.scene_type === value;
    });
  }

  function renderSummary() {
    const comparisons = scenes.map(compare);
    const totalRisk = scenes.filter((scene) => scene.ground_truth.length > 0).length;
    const correct = comparisons.filter((item) => item.status === "correct").length;
    const partial = comparisons.filter((item) => item.status === "partial").length;
    const failure = comparisons.filter((item) => item.status === "failure").length;
    const stats = [
      ["样本总数", scenes.length],
      ["风险样本", totalRisk],
      ["风险类别", rules.length],
      ["识别正确", correct],
      ["需分析案例", partial + failure],
    ];
    summaryGrid.innerHTML = stats
      .map(([label, value]) => `<article class="stat-card"><span>${label}</span><strong>${value}</strong></article>`)
      .join("");
  }

  function renderSceneList() {
    const items = filteredScenes();
    if (!items.some((scene) => scene.id === currentSceneId)) {
      currentSceneId = items[0]?.id || scenes[0]?.id;
    }

    sceneList.innerHTML = items
      .map((scene) => {
        const itemCompare = compare(scene);
        const active = scene.id === currentSceneId ? " active" : "";
        const riskNames = scene.ground_truth.map((risk) => risk.type).join("、") || "无";
        return `
          <button class="scene-card${active}" type="button" data-id="${scene.id}">
            <span class="scene-card-title">
              <span>${scene.id} ${scene.title}</span>
              <span class="badge info">${scene.scene_type}</span>
            </span>
            <span class="scene-meta">${scene.summary}</span>
            <span class="badge-row">
              ${riskBadge(scene)}
              ${statusBadge(itemCompare.status)}
              <span class="badge">风险: ${riskNames}</span>
            </span>
          </button>
        `;
      })
      .join("");

    sceneList.querySelectorAll(".scene-card").forEach((button) => {
      button.addEventListener("click", () => {
        currentSceneId = button.dataset.id;
        render();
      });
    });
  }

  function renderRiskList(title, risks) {
    if (!risks || risks.length === 0) {
      return `
        <div class="result-box">
          <h3>${title}</h3>
          <p class="empty-state">未发现风险。</p>
        </div>
      `;
    }
    return `
      <div class="result-box">
        <h3>${title}</h3>
        ${risks
          .map(
            (risk) => `
              <article class="risk-item">
                <div class="badge-row">
                  <span class="badge risk">${risk.type}</span>
                  <span class="badge info">${risk.level}风险</span>
                </div>
                <p><strong>相关物体：</strong>${(risk.objects || []).join("、")}</p>
                <p><strong>位置：</strong>${risk.location}</p>
                <p><strong>依据：</strong>${risk.reason}</p>
                <p><strong>建议：</strong>${risk.suggestion}</p>
              </article>
            `
          )
          .join("")}
      </div>
    `;
  }

  function renderDetail() {
    const scene = scenes.find((item) => item.id === currentSceneId) || scenes[0];
    if (!scene) {
      detailPanel.innerHTML = '<p class="empty-state">没有可展示的样本。</p>';
      return;
    }

    const itemCompare = compare(scene);
    const result = modelResults[scene.id] || { has_risk: false, risks: [] };
    const issues = [];
    if (itemCompare.missed.length) issues.push(`漏检：${itemCompare.missed.map((risk) => risk.type).join("、")}`);
    if (itemCompare.falsePositive.length) issues.push(`误检：${itemCompare.falsePositive.map((risk) => risk.type).join("、")}`);
    if (itemCompare.levelMismatch.length) issues.push(`等级不一致：${itemCompare.levelMismatch.map((risk) => risk.type).join("、")}`);
    if (!issues.length) issues.push("人工标注与模型输出一致。");

    detailPanel.innerHTML = `
      <div class="detail-hero">
        <div class="scene-image-wrap">
          <img src="${scene.image}" alt="${scene.title}" />
        </div>
        <div class="detail-copy">
          <div class="badge-row">
            <span class="badge info">${scene.scene_type}</span>
            ${riskBadge(scene)}
            ${statusBadge(itemCompare.status)}
          </div>
          <div>
            <h2>${scene.id} ${scene.title}</h2>
            <p>${scene.summary}</p>
          </div>
          <div>
            <h3>场景物体</h3>
            <div class="objects-list">${scene.objects.map((item) => `<span class="badge">${item}</span>`).join("")}</div>
          </div>
          <div>
            <h3>模拟 VLM JSON</h3>
            <pre class="report-pre">${escapeHtml(JSON.stringify(result, null, 2))}</pre>
          </div>
        </div>
      </div>
      <div class="result-grid">
        ${renderRiskList("人工标注", itemCompare.truth)}
        ${renderRiskList("模拟 VLM 输出", itemCompare.predicted)}
      </div>
      <div class="compare-box">
        <h3>对比结论</h3>
        <ul class="compare-list">
          ${issues.map((issue) => `<li>${issue}</li>`).join("")}
          ${result.note ? `<li>${result.note}</li>` : ""}
        </ul>
      </div>
    `;
  }

  function renderRules() {
    rulesGrid.innerHTML = rules
      .map(
        (rule) => `
          <article class="rule-card">
            <h3>${rule.name}</h3>
            <p>${rule.rule}</p>
            <p><strong>等级提示：</strong>${rule.level_hint}</p>
          </article>
        `
      )
      .join("");
  }

  function renderFailures() {
    const failures = scenes
      .map((scene) => ({ scene, itemCompare: compare(scene), result: modelResults[scene.id] || {} }))
      .filter((item) => item.itemCompare.status !== "correct" || item.result.note);

    failureGrid.innerHTML = failures
      .map(({ scene, itemCompare, result }) => {
        const reasons = [];
        if (itemCompare.missed.length) reasons.push(`漏检 ${itemCompare.missed.map((risk) => risk.type).join("、")}`);
        if (itemCompare.falsePositive.length) reasons.push(`误检 ${itemCompare.falsePositive.map((risk) => risk.type).join("、")}`);
        if (itemCompare.levelMismatch.length) reasons.push(`等级低估或高估 ${itemCompare.levelMismatch.map((risk) => risk.type).join("、")}`);
        if (result.note) reasons.push(result.note);
        return `
          <article class="failure-card">
            <div class="badge-row">
              <span class="badge info">${scene.id}</span>
              ${statusBadge(itemCompare.status)}
            </div>
            <h3>${scene.title}</h3>
            <p>${reasons.join("；")}</p>
            <p><strong>改进方向：</strong>补充视角、细化距离规则，或在 Prompt 中要求模型说明证据是否充分。</p>
          </article>
        `;
      })
      .join("");
  }

  function exportReport() {
    const scene = scenes.find((item) => item.id === currentSceneId);
    const report = {
      scene,
      model_result: modelResults[currentSceneId],
      comparison: compare(scene),
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${currentSceneId}_inspection_report.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function render() {
    renderSummary();
    renderSceneList();
    renderDetail();
    renderRules();
    renderFailures();
  }

  filter.addEventListener("change", render);
  exportButton.addEventListener("click", exportReport);
  render();
})();
