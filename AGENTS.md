# AI 视觉室内巡检项目开发规范

## 1. 项目目标

本项目来自“基于 AI 视觉的虚拟室内巡检实践”课程任务，目标是构建一个小型但完整的室内安全巡检系统闭环：

```text
构造室内场景 -> 生成风险样本 -> 调用 VLM 识别 -> 约束结构化输出 -> 形成巡检报告 -> 分析成功与失败案例
```

后续开发应优先保证课程要求完整闭环，而不是追求复杂功能堆叠。所有新增功能都应服务于以下能力：

- 可控地管理室内场景数据。
- 清晰定义风险类别、风险规则和人工标注。
- 支持不同 VLM 或不同 Prompt 的识别对比。
- 结构化保存模型输出和巡检报告。
- 能展示成功案例、失败案例和改进分析。

## 2. 当前 Demo 基线

当前 `demo/` 已经实现一个可直接打开的静态演示版本：

- `demo/index.html`：前端展示入口。
- `demo/app.js`：场景选择、模型结果展示、人工标注对比、失败案例分析。
- `demo/styles.css`：页面样式。
- `demo/data.js`：前端直接加载的数据。
- `demo/data/*.json`：风险规则、场景标注、模拟 VLM 输出。
- `demo/assets/scenes/*.svg`：12 个可控虚拟室内场景。
- `demo/prompts/risk_inspection_prompt.md`：结构化巡检 Prompt。
- `demo/vlm_call.py`：可选真实 VLM 调用入口。
- `demo/tools/generate_demo_assets.py`：生成 demo 数据和 SVG 场景。

后续开发不得破坏这个最小可行 demo。新增复杂功能时，应保留“无需 API Key 也能演示”的模拟模式。

## 3. 基于 Demo 的优先改进点

### 3.1 数据从静态模拟扩展为可配置数据源

当前 demo 使用内置 SVG 样本和模拟 VLM 输出。后续应支持：

- 上传本地图片。
- 导入文件夹图片。
- 导入公开数据集或自建数据集。
- 导入多视角图片组。
- 导入短视频并抽帧。
- 将人工标注、模型输出、评测结果分离保存。

建议新增目录：

```text
datasets/
  custom/
  homesafe_like/
  behavior_like/
  esi_like/
outputs/
  vlm_results/
  reports/
  evaluations/
configs/
  providers/
  prompts/
```

### 3.2 提供自助选择 API 的接口

当前 `demo/vlm_call.py` 只提供一个 OpenAI-compatible 的基础入口。后续应做成可选择 provider 的统一接口。

建议抽象为：

```python
class VLMProvider:
    name: str

    def inspect(self, images: list[Path], prompt: str, options: dict) -> dict:
        ...
```

必须支持的 provider 类型：

- `mock`：无网络、无 Key 的本地模拟输出，用于课堂演示。
- `openai`：OpenAI Responses API 或兼容视觉接口。
- `qwen`：通义千问/Qwen-VL 或 OpenAI-compatible 服务。
- `gemini`：Google Gemini 视觉模型。
- `ollama`：本地视觉模型，例如 Qwen-VL、LLaVA 类模型。
- `custom_http`：用户自定义 endpoint、header、payload 模板。

配置文件建议使用 JSON 或 YAML：

```json
{
  "active_provider": "openai",
  "providers": {
    "openai": {
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-4.1-mini",
      "api_key_env": "OPENAI_API_KEY"
    },
    "qwen": {
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "qwen-vl-plus",
      "api_key_env": "DASHSCOPE_API_KEY"
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "qwen2.5vl:7b"
    }
  }
}
```

API Key 不得写入仓库。只能从环境变量、`.env.local` 或用户手动输入读取。若需要保存配置，只保存环境变量名，不保存密钥值。

### 3.3 数据集泛化

后续不要把代码写死为 `S01`、`宿舍`、`触电风险` 这类 demo 字段。应建立通用数据结构。

推荐场景样本 schema：

```json
{
  "sample_id": "unique_id",
  "dataset": "custom",
  "scene_type": "宿舍 | 厨房 | 客厅 | 实验室 | 走廊 | 其他",
  "media": [
    {
      "type": "image",
      "path": "assets/scenes/S02.svg",
      "view": "front",
      "timestamp": null
    }
  ],
  "objects": ["水杯", "插座", "书桌"],
  "regions": ["桌面", "墙面插座区域"],
  "ground_truth": [
    {
      "risk_type": "electric_shock",
      "risk_name": "触电风险",
      "objects": ["水杯", "插座"],
      "location": "书桌右侧靠墙区域",
      "level": "高",
      "rule_id": "electric_shock_001",
      "reason": "液体容器靠近插座。",
      "suggestion": "将水杯移到远离插座的位置。"
    }
  ],
  "metadata": {
    "source": "generated | real_photo | public_dataset",
    "license": "",
    "created_at": "2026-06-30"
  }
}
```

推荐模型输出 schema：

```json
{
  "sample_id": "unique_id",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "prompt_id": "risk_inspection_v1",
  "has_risk": true,
  "risks": [
    {
      "risk_type": "electric_shock",
      "risk_name": "触电风险",
      "objects": ["水杯", "插座"],
      "location": "书桌右侧靠墙区域",
      "level": "高",
      "reason": "液体容器靠近插座，触发规则。",
      "suggestion": "移开水杯。"
    }
  ],
  "evidence_sufficiency": "充分",
  "uncertain_points": [],
  "raw_response": {}
}
```

### 3.4 风险规则标准化

风险规则应独立维护，不要散落在前端、Prompt 和 Python 代码里。

建议统一放在：

```text
configs/risk_rules.json
```

每条规则至少包含：

- `rule_id`
- `risk_type`
- `risk_name`
- `description`
- `trigger_conditions`
- `level_policy`
- `positive_examples`
- `negative_examples`

这样后续可以从同一份规则生成 Prompt、前端说明和评测逻辑。

### 3.5 多 Prompt 和多模型对比

课程评价强调 Prompt 与模型调用、输出稳定性和失败分析。后续应支持：

- 同一数据集用不同 Prompt 跑一遍。
- 同一 Prompt 用不同模型跑一遍。
- 单图输入与多视角输入对比。
- 记录每次运行的配置、模型、时间、成本估计。

推荐 run 记录：

```json
{
  "run_id": "20260630_openai_prompt_v1",
  "dataset": "custom_demo",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "prompt_id": "risk_inspection_v1",
  "input_mode": "single_image",
  "created_at": "2026-06-30T16:40:00+08:00"
}
```

## 4. 推荐架构

建议从静态 demo 逐步演进为以下结构：

```text
.
├── AGENTS.md
├── demo/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── data/
│   ├── assets/
│   ├── prompts/
│   └── tools/
├── src/
│   ├── datasets/
│   │   ├── loaders.py
│   │   ├── schema.py
│   │   └── exporters.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── mock_provider.py
│   │   ├── openai_provider.py
│   │   ├── qwen_provider.py
│   │   ├── gemini_provider.py
│   │   └── ollama_provider.py
│   ├── prompts/
│   │   ├── builder.py
│   │   └── templates/
│   ├── evaluation/
│   │   ├── compare.py
│   │   └── metrics.py
│   └── reports/
│       └── render.py
├── configs/
│   ├── risk_rules.json
│   ├── providers.example.json
│   └── prompts/
├── datasets/
├── outputs/
└── tests/
```

如果项目仍保持轻量，也可以先不引入完整 `src/`，但数据 schema、provider 抽象和输出目录应尽早建立。

## 5. 前端开发规范

前端应优先服务“巡检系统”体验，而不是做营销页。

必须保留或支持：

- 场景列表。
- 场景图像或视频展示。
- 人工标注展示。
- 模型输出展示。
- 对比结论：正确、漏检、误检、等级错误。
- 失败案例分析。
- 风险规则说明。
- 导出报告。

建议新增：

- API provider 选择面板。
- Prompt 选择面板。
- 图片上传入口。
- 数据集导入入口。
- 批量运行按钮。
- 运行历史列表。
- 结果筛选：按风险类型、场景类型、错误类型、模型名称筛选。

前端不要把密钥写入浏览器本地代码。如果需要用户输入 API Key，默认仅保存在当前会话内；若使用本地服务，由后端读取环境变量。

## 6. 后端与脚本规范

Python 脚本应做到：

- 读取配置，而不是硬编码模型和路径。
- 输出 JSON 文件，便于前端和报告复用。
- 保留原始模型响应，便于排查。
- 对模型输出做 JSON 解析和字段校验。
- 当模型输出不符合格式时，保存错误而不是直接丢弃。

推荐命令形式：

```powershell
python -m src.run_inspection --dataset datasets/custom --provider openai --prompt risk_inspection_v1 --output outputs/vlm_results/run_id
python -m src.evaluate --ground-truth datasets/custom/annotations.json --predictions outputs/vlm_results/run_id
python -m src.reports.render --run outputs/vlm_results/run_id --output outputs/reports/run_id.html
```

## 7. 评测规范

至少统计：

- 样本数。
- 风险样本数。
- 正常样本数。
- 风险类别覆盖数。
- 漏检数。
- 误检数。
- 风险类型匹配数。
- 风险等级错误数。
- 失败案例列表。

课程展示中必须保留至少 3 个失败案例，并说明：

- 错误类型：漏检、误检、空间关系错误、等级错误、输出格式错误。
- 可能原因：遮挡、视角不足、小目标、Prompt 规则不清、模型幻觉。
- 改进方案：补充视角、细化规则、要求证据充分性判断、更换模型、引入检测 baseline。

## 8. 数据集接入策略

### 8.1 自建数据

自建数据是课程最推荐路径。要求：

- 每张图必须有人工标注。
- 正常样本和风险样本成对设计。
- 每类风险至少有 2 到 3 个样本。
- 图片来源、修改方式和风险设计要记录。

### 8.2 HomeSafeBench 类数据

适合借鉴家庭安全风险类别、自由探索、多视角评测。接入时应转换为本项目 schema：

- hazard category -> `risk_type`
- first-person observation -> `media`
- hazard object -> `objects`
- exploration result -> `metadata` 或多视角字段

### 8.3 BEHAVIOR-1K 类数据

适合借鉴场景、物体状态、活动定义。接入重点不是复现仿真，而是提取：

- 室内场景类型。
- 物体类别。
- 物体状态。
- 正常/异常状态对照。

### 8.4 ESI-BENCH 类数据

适合借鉴空间智能评测。接入重点：

- 遮挡。
- 距离。
- 视角变化。
- 连通性和通行关系。
- 单视角与多视角结果差异。

所有外部数据集都要记录来源和许可。不要把大体积公开数据直接塞进仓库，优先写下载说明或转换脚本。

## 9. 安全与隐私

- 不要提交 API Key、账号、cookie、真实个人隐私照片。
- 如果使用宿舍、实验室真实照片，应模糊人脸、姓名、学号、屏幕内容等敏感信息。
- 真实场景照片应只用于课程演示，不要公开上传到无关平台。
- 外部 API 调用前应确认图片内容是否适合上传。
- 输出报告中不要包含密钥、完整本地用户路径或私人信息。

## 10. 代码质量与验证

每次修改后至少做以下检查：

- 前端：确认 `demo/index.html` 能正常打开，场景、规则、结果不为空。
- 数据：确认 JSON 可解析。
- Python：确认脚本语法正确，mock 模式可运行。
- VLM：真实调用失败时保留错误信息，并不影响 mock 演示。

推荐轻量检查命令：

```powershell
python .\demo\vlm_call.py --mock-scene S02
python .\demo\tools\generate_demo_assets.py
```

如果后续引入 `src/` 和测试，应增加：

```powershell
python -m pytest
```

## 11. 文档与课程交付

项目文档应持续维护：

- `README.md`：如何运行项目。
- `AGENTS.md`：开发规范和任务边界。
- `docs/task_analysis.md`：课程任务拆解。
- `docs/prompt_design.md`：Prompt 版本和设计理由。
- `docs/failure_cases.md`：失败案例分析。
- `docs/final_report.md`：最终课程报告草稿。

最终交付材料至少包含：

- 场景图像或视频数据。
- 风险类别和规则说明。
- Prompt 设计文档。
- 代码、Notebook 或演示程序。
- 模型识别结果样例。
- 至少 3 个失败案例分析。
- 最终展示 PPT 或课程报告。

## 12. 后续开发优先级

建议按以下顺序推进：

1. 将当前 demo 的数据 schema 稳定下来。
2. 增加 provider 配置和 API 自助选择界面。
3. 支持上传图片并调用真实 VLM。
4. 支持批量运行一个数据集。
5. 增加自动评测和失败案例筛选。
6. 支持多 Prompt、多模型对比。
7. 支持多视角或短视频输入。
8. 生成课程报告或展示 PPT 所需的数据摘要。

任何时候都应保留最小闭环可运行：即使没有网络、没有 API Key，也能用 mock 数据演示完整流程。
