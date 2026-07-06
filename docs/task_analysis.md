# 课程任务拆解与系统分析

本文档对「基于 AI 视觉的虚拟室内巡检实践」课程任务进行拆解，说明系统架构、已完成功能、技术选型，并对照课程评价要点进行自查。

---

## 1. 课程任务拆解

课程要求构建一个完整的室内安全巡检系统闭环：

```
构造室内场景 -> 生成风险样本 -> 调用 VLM 识别 -> 约束结构化输出 -> 形成巡检报告 -> 分析成功与失败案例
```

### 1.1 构造室内场景

**任务目标**：可控地生成室内场景数据，覆盖多种场景类型和风险类别。

**实现方式**：

- 使用 SVG 矢量图程序化生成 12 个虚拟室内场景，覆盖宿舍、厨房、客厅、实验室、走廊 5 种场景类型。
- 每个场景包含区域划分（如桌面、床、门、台面、通道）和物体摆放（如水杯、插座、化学品、电线）。
- 场景生成脚本位于 `demo/tools/generate_demo_assets.py`，通过代码定义场景结构和物体位置，确保可控性和可复现性。
- 场景图像输出到 `demo/assets/scenes/S01.svg` 至 `S12.svg`。

### 1.2 生成风险样本

**任务目标**：为每个场景设计人工标注，区分正常样本和风险样本。

**实现方式**：

- 12 个场景中包含 10 个风险样本和 2 个正常样本（S01 宿舍正常、S05 厨房正常）。
- 覆盖 6 类风险：触电风险、火灾风险、通行/绊倒风险、坠物风险、危险物暴露、清洁度异常。
- 每类风险至少有 1-2 个样本，确保类别覆盖完整。
- 人工标注包含风险类型、涉及物体、位置、等级、原因、建议 6 个字段，结构化保存在 `demo/data/scenes.json` 中。
- 正常样本和风险样本成对设计（如 S04 厨房火灾风险 vs S05 厨房正常），便于对比。

### 1.3 调用 VLM 识别

**任务目标**：将场景图像输入视觉语言模型，获取风险识别结果。

**实现方式**：

- 抽象出 `VLMProvider` 基类（`src/providers/base.py`），统一接口为 `inspect(images, prompt, options) -> ProviderResult`。
- 实现 4 个 provider：
  - `MockProvider`：无网络、无 API Key 的本地模拟输出，返回预设结果，用于课堂演示。
  - `QwenProvider`：通过 DashScope OpenAI 兼容接口调用通义千问 Qwen-VL 视觉模型。
  - `OpenAI Provider`：通过 OpenAI 兼容接口调用 GPT-4.1-mini 等视觉模型（配置已就绪）。
  - `Ollama Provider`：调用本地 Ollama 部署的 Qwen2.5-VL / LLaVA 模型（配置已就绪）。
- Provider 工厂（`src/providers/factory.py`）根据配置文件动态创建实例，支持运行时传入 API Key。
- 图片上传通过 FastAPI 后端的 `/api/inspect` 接口实现，支持 JPG/PNG/SVG 格式。

### 1.4 约束结构化输出

**任务目标**：让 VLM 输出固定格式的 JSON，便于后续处理和评测。

**实现方式**：

- 设计 3 版 Prompt（v1 基线版、v2 细化规则版、v3 带正负示例版），均要求输出固定 JSON schema。
- JSON schema 包含 `has_risk`、`risks`（含 type/objects/location/level/reason/suggestion）、`evidence_sufficiency`、`uncertain_points` 字段。
- 后端 `validate_model_output` 函数做字段校验，校验失败保留错误信息但不丢弃结果。
- `QwenProvider` 的 `_parse_json` 函数实现多级 JSON 解析回退（直接解析 -> 代码块提取 -> 花括号匹配），保证鲁棒性。
- 详见 `docs/prompt_design.md`。

### 1.5 形成巡检报告

**任务目标**：将模型输出结构化保存，形成可查阅的巡检报告。

**实现方式**：

- 每次巡检运行生成一个 run 目录（`outputs/vlm_results/{run_id}/`），包含 `results.json`。
- `results.json` 记录 run 元信息（run_id、dataset、provider、model、prompt_id、时间戳）和每个样本的完整结果（人工标注、模型输出、原始响应）。
- 单次巡检结果保存为 `outputs/vlm_results/inspect_{timestamp}_{provider}.json`。
- 前端 `demo/index.html` 展示场景列表、人工标注、模型输出对比和失败案例分析。
- 前端 `demo/inspect.html` 支持上传图片并实时查看结构化识别结果。

### 1.6 分析成功与失败案例

**任务目标**：自动评测模型输出与人工标注的差异，筛选并分析失败案例。

**实现方式**：

- 评测模块（`src/evaluation/metrics.py`）逐样本对比人工标注和模型输出，判定错误类型：漏检、误检、等级错误、输出格式错误。
- 失败案例筛选（`src/evaluation/compare.py`）为每个失败案例补充可能原因和改进方案，按错误类型分组。
- 评测结果保存到 `outputs/evaluations/{run_id}_evaluation.json` 和 `{run_id}_failures.json`。
- 多 run 对比（`src/evaluation/compare_runs.py`）支持横向对比不同 Prompt 或不同模型的评测指标，找出差异样本。
- 前端 `demo/batch.html` 和 `demo/compare.html` 提供批量评测和多 Prompt 对比的可视化界面。
- 3 个典型失败案例的深度分析见 `docs/failure_cases.md`。

---

## 2. 系统架构说明

系统采用分层架构，从静态 demo 逐步演进为完整的后端服务架构：

```
.
├── demo/                    # Demo 层：静态演示与前端页面
│   ├── index.html           # 场景列表、标注对比、失败案例分析
│   ├── inspect.html         # 实时巡检（上传图片 + 选择 provider）
│   ├── batch.html           # 批量评测面板
│   ├── compare.html         # 多 Prompt / 多模型对比面板
│   ├── app.js / inspect.js / batch.js / compare.js
│   ├── styles.css
│   ├── data.js              # 前端直接加载的数据（静态模式）
│   ├── data/                # 风险规则、场景标注、mock VLM 结果
│   ├── assets/scenes/       # 12 个 SVG 虚拟场景
│   ├── prompts/             # 原始巡检 Prompt
│   ├── vlm_call.py          # 命令行 VLM 调用入口
│   └── tools/               # 数据生成脚本
├── src/                     # 核心层：后端业务逻辑
│   ├── providers/           # VLM Provider 抽象与实现
│   │   ├── base.py          # VLMProvider 抽象基类
│   │   ├── factory.py       # Provider 工厂
│   │   ├── mock_provider.py # 本地模拟 provider
│   │   └── qwen_provider.py # Qwen-VL provider
│   ├── datasets/            # 数据 schema 与加载器
│   │   ├── schema.py        # SampleSchema / ModelOutput / 字段校验
│   │   └── loaders.py       # 数据集加载器
│   ├── prompts/             # Prompt 构建器
│   │   └── builder.py       # PromptBuilder
│   ├── evaluation/          # 评测模块
│   │   ├── metrics.py       # 指标计算
│   │   ├── compare.py       # 失败案例筛选与分析
│   │   └── compare_runs.py  # 多 run 横向对比
│   ├── reports/             # 报告生成（预留）
│   ├── run_inspection.py    # 批量巡检运行器
│   └── server.py            # FastAPI 后端服务
├── configs/                 # 配置层
│   ├── risk_rules.json      # 风险规则（唯一来源）
│   ├── providers.example.json  # Provider 配置模板
│   └── prompts/             # 3 版 Prompt 模板
├── datasets/                # 数据层
│   ├── custom/              # 自建数据集
│   ├── homesafe_like/       # HomeSafeBench 类数据
│   ├── behavior_like/       # BEHAVIOR-1K 类数据
│   └── esi_like/            # ESI-BENCH 类数据
├── outputs/                 # 输出层
│   ├── vlm_results/         # VLM 调用结果（按 run 组织）
│   ├── evaluations/         # 评测结果与失败案例
│   └── reports/             # 巡检报告（预留）
└── tests/                   # 测试
```

### 架构特点

1. **最小闭环保底**：即使没有 Python 环境和网络，双击 `demo/index.html` 也能查看完整的静态演示。
2. **配置驱动**：Provider、风险规则、Prompt 均通过配置文件管理，不硬编码。
3. **数据与逻辑分离**：人工标注、模型输出、评测结果分别存储，互不污染。
4. **可扩展 Provider**：新增 provider 只需继承 `VLMProvider` 并在配置文件中注册。

---

## 3. 已完成功能清单

按开发阶段组织，对照 README 中的开发计划：

### 阶段 A：数据 schema 稳定与基础设施

- [x] 定义通用数据 schema（`src/datasets/schema.py`）：`SampleSchema`、`ModelOutput`、`GroundTruth`、`RiskItem`，支持 dict 序列化与反序列化。
- [x] 风险规则抽离到独立配置文件（`configs/risk_rules.json`），包含 rule_id、触发条件、等级策略、正负示例。
- [x] 12 个虚拟室内场景 SVG 生成与人工标注（`demo/tools/generate_demo_assets.py`）。
- [x] Provider 配置模板（`configs/providers.example.json`），支持 mock/qwen/openai/ollama 四种 provider。
- [x] Prompt 构建器（`src/prompts/builder.py`），支持从规则文件和模板文件加载。
- [x] 数据集加载器（`src/datasets/loaders.py`），支持 demo 内置场景和自定义数据集。

### 阶段 B：Provider 抽象与实时巡检

- [x] `VLMProvider` 抽象基类（`src/providers/base.py`），统一 `inspect` 接口和 `ProviderResult` 返回结构。
- [x] `MockProvider` 实现：无网络、无 API Key 的本地模拟输出。
- [x] `QwenProvider` 实现：通过 DashScope OpenAI 兼容接口调用 Qwen-VL，支持 base64 图片编码、多级 JSON 解析。
- [x] Provider 工厂（`src/providers/factory.py`）：根据配置动态创建实例，支持运行时传入 API Key。
- [x] FastAPI 后端服务（`src/server.py`）：提供 provider 列表、prompt 列表、风险规则、图片上传巡检等 API。
- [x] 实时巡检前端页面（`demo/inspect.html`）：上传图片、选择 provider、输入 API Key、查看结构化结果。
- [x] API Key 安全处理：仅会话内使用，不落盘；配置文件只存环境变量名。

### 阶段 C：批量运行与自动评测

- [x] 批量巡检运行器（`src/run_inspection.py`）：遍历数据集逐样本调用 VLM，记录 run 元信息和统计。
- [x] 评测指标计算（`src/evaluation/metrics.py`）：准确率、漏检数、误检数、等级错误数、格式错误数、风险类别覆盖。
- [x] 失败案例筛选与分析（`src/evaluation/compare.py`）：按错误类型分组，补充可能原因和改进方案。
- [x] 批量评测 API（`POST /api/run_batch`）：一键运行数据集并自动评测。
- [x] 历史运行管理：`GET /api/runs` 列出所有 run，`GET /api/runs/{run_id}` 查看详情。
- [x] 批量评测前端页面（`demo/batch.html`）。
- [x] 评测结果持久化到 `outputs/evaluations/`。

### 阶段 D：多 Prompt / 多模型对比

- [x] 多 run 横向对比（`src/evaluation/compare_runs.py`）：构建逐样本对比表，找出差异样本，标注最佳 run。
- [x] 多 Prompt 批量运行 API（`POST /api/run_multi_batch`）：接收多个 prompt_id，逐个运行并自动对比。
- [x] 任意 run 对比 API（`POST /api/compare`）：传入多个 run_id 进行对比。
- [x] 自动对比 API（`GET /api/compare/auto`）：按数据集/provider/prompt 筛选历史 run 自动对比。
- [x] 多 Prompt 对比前端页面（`demo/compare.html`）。
- [x] 3 版 Prompt 模板（`configs/prompts/risk_inspection_v1.md`、`v2.md`、`v3.md`）。
- [x] 已有 mock v1 vs v2 的对比运行数据。

---

## 4. 技术选型说明

### 4.1 后端：Python FastAPI

**选型理由**：

- FastAPI 原生支持异步、文件上传、自动生成 OpenAPI 文档，适合快速构建原型 API。
- Python 生态对 AI/ML 库支持完善，后续接入更多模型或工具链无障碍。
- 类型提示与 Pydantic 模型提升代码可靠性。
- 轻量级，单文件即可启动服务（`python -m src.server`）。

**核心依赖**：仅使用标准库（`urllib`、`json`、`pathlib`）实现 HTTP 调用和 JSON 解析，避免引入重量级 SDK。FastAPI 和 Uvicorn 是唯一的第三方后端依赖。

### 4.2 前端：原生 JavaScript

**选型理由**：

- 课程项目不需要复杂前端框架，原生 JS + HTML 足够实现场景列表、结果展示、对比面板等功能。
- 无构建步骤，双击 HTML 即可打开静态 demo，降低演示门槛。
- 前端只负责展示和交互，不处理密钥和模型调用逻辑，安全性更好。
- 4 个页面（index/inspect/batch/compare）各有独立 JS 文件，职责清晰。

### 4.3 视觉模型：Qwen-VL

**选型理由**：

- 通义千问 Qwen-VL 是国产视觉语言模型，通过 DashScope 提供 OpenAI 兼容接口，接入成本低。
- 支持 base64 图片输入和结构化 JSON 输出，满足巡检场景需求。
- 同时支持云端 API（qwen-vl-plus）和本地部署（通过 Ollama 部署 qwen2.5vl:7b），灵活适配不同环境。
- API Key 通过环境变量读取，不写入代码仓库，符合安全规范。

**调用方式**：使用标准 `urllib.request` 发送 HTTP 请求，将图片编码为 base64 data URL，content 格式为 `[{type: text}, {type: image_url}]`，与 OpenAI chat/completions 接口完全兼容。

### 4.4 数据格式：SVG + JSON

**选型理由**：

- 场景图像使用 SVG 矢量图而非位图：可控、可编辑、体积小，且可通过代码精确控制物体位置和空间关系。
- 所有结构化数据（场景标注、风险规则、模型输出、评测结果）均使用 JSON 格式，便于前端加载、后端处理和版本管理。
- 不依赖数据库，JSON 文件即可满足课程级数据存储需求。

---

## 5. 课程评价要点对照

### 5.1 闭环完整性

| 闭环环节 | 实现状态 | 对应文件 |
|---------|---------|---------|
| 构造室内场景 | 已完成 | `demo/tools/generate_demo_assets.py`、`demo/assets/scenes/*.svg` |
| 生成风险样本 | 已完成 | `demo/data/scenes.json`、`configs/risk_rules.json` |
| 调用 VLM 识别 | 已完成 | `src/providers/`、`src/server.py` |
| 约束结构化输出 | 已完成 | `configs/prompts/*.md`、`src/datasets/schema.py` |
| 形成巡检报告 | 已完成 | `outputs/vlm_results/`、`demo/index.html` |
| 分析成功与失败案例 | 已完成 | `src/evaluation/`、`outputs/evaluations/`、`docs/failure_cases.md` |

闭环完整，且保留「无网络、无 API Key 也能用 mock 模式演示完整流程」的保底能力。

### 5.2 Prompt 设计

- 设计了 3 版递进式 Prompt，每版有明确的设计理由和改进点。
- 输出 JSON schema 统一，支持前端展示和自动评测。
- 约束策略覆盖防止过度报警、证据充分性判断、等级标准三个方面。
- 支持 v2 增加距离阈值、v3 增加正负示例和等级表。
- 详见 `docs/prompt_design.md`。

### 5.3 失败分析

- 保留 3 个典型失败案例，覆盖误检、等级错误、漏检三类错误。
- 每个案例包含错误类型、场景描述、人工标注、模型输出、可能原因、改进方案。
- 可能原因覆盖遮挡、视角不足、小目标、Prompt 规则不清、模型幻觉。
- 改进方案覆盖补充视角、细化规则、证据充分性判断、更换模型、检测 baseline。
- 详见 `docs/failure_cases.md`。

### 5.4 数据集泛化

- 建立通用数据 schema（`SampleSchema`），不写死场景 ID、场景类型或风险类别。
- 预留 4 类数据集目录：`custom/`（自建）、`homesafe_like/`、`behavior_like/`、`esi_like/`。
- 数据集加载器支持 demo 内置场景和自定义路径。
- 风险规则独立维护在 `configs/risk_rules.json`，可从同一份规则生成 Prompt、前端说明和评测逻辑。
- `datasets/custom/` 已支持上传自定义图片。

---

## 6. 后续展望

按 AGENTS.md 中的优先级，后续可推进的工作：

1. **多视角输入**：为 S12 等遮挡场景增加侧面/俯视视角图片，验证多视角对漏检的改善。
2. **真实数据集接入**：将 HomeSafeBench、BEHAVIOR-1K、ESI-BENCH 类数据转换为本项目 schema。
3. **报告生成**：实现 `src/reports/render.py`，从 run 结果生成 HTML 巡检报告。
4. **测试覆盖**：为 schema 校验、JSON 解析、评测指标计算编写单元测试。
5. **课程报告**：汇总评测数据、失败案例和 Prompt 对比结果，生成最终课程报告草稿。
