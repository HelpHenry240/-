# AI 视觉室内巡检系统

这是一个面向“基于 AI 视觉的虚拟室内巡检实践”课程任务的完整 demo 项目。项目围绕一个最小闭环展开：

```text
构造室内场景 -> 生成风险样本 -> 调用 VLM 识别 -> 约束结构化输出 -> 自动评测与对比 -> 失败案例分析
```

当前版本保留无网络、无 API Key 也能演示的 `mock` 模式，同时提供 FastAPI 后端、Qwen/OpenAI-compatible Provider、批量运行、自动评测、多 Prompt/多 run 对比和游戏化巡检入口。

## 当前进展

- `demo/index.html`：静态课程演示入口，展示 12 个虚拟室内场景、风险规则、人工标注、模型输出和失败案例。
- `demo/inspect.html`：上传单图或多视角图片，选择 Provider 和 Prompt 后执行实时巡检。
- `demo/annotate.html`：上传自建图片并保存人工标注，标注数据用于后续数据集评测。
- `demo/batch.html`：选择数据集、Provider、Prompt 后批量运行巡检。
- `demo/compare.html`：对比不同 run、Prompt 或模型的评测结果。
- `src/server.py`：FastAPI 服务，提供巡检、标注、数据集、批量运行、运行历史和对比接口。
- `src/providers/`：Provider 抽象，当前支持 `mock` 和 OpenAI-compatible 的 `qwen/openai/ollama` 配置方式。
- `src/evaluation/`：统计漏检、误检、等级错误、格式错误、失败案例和 run 对比。
- `game/`：游戏化巡逻机器人入口，复用后端 `/api/inspect` 进行风险识别。
- `docs/`：课程任务拆解、Prompt 设计、失败案例分析、优化计划和展示材料。

## 快速演示

### 方式 1：静态 Demo

不需要安装依赖，也不需要网络。直接双击打开：

```text
demo/index.html
```

这个入口适合课堂展示最小闭环：场景图像、人工标注、mock 模型结果、对比结论和失败案例分析都已内置。

### 方式 2：启动后端体验完整功能

建议使用 Python 3.10 或更高版本。

```powershell
pip install -r requirements.txt
py -m src.server
```

服务启动后访问：

| 页面 | 地址 | 用途 |
|------|------|------|
| 静态演示 | http://localhost:8000/demo/index.html | 课程闭环展示 |
| 实时巡检 | http://localhost:8000/demo/inspect.html | 上传图片并调用 VLM |
| 自建标注 | http://localhost:8000/demo/annotate.html | 上传图片并保存人工标注 |
| 批量运行 | http://localhost:8000/demo/batch.html | 对整个数据集批量巡检 |
| 结果对比 | http://localhost:8000/demo/compare.html | 对比多个 run 的效果 |
| 巡检游戏 | http://localhost:8000/game/index.html | 游戏化巡逻机器人体验 |
| API 文档 | http://localhost:8000/docs | FastAPI 自动文档 |

## Provider 与 API Key

默认 Provider 是 `mock`，无需网络和 API Key。真实模型调用通过 `configs/providers.example.json` 配置，建议复制为本地配置文件：

```powershell
Copy-Item configs/providers.example.json configs/providers.json
```

API Key 不要写入仓库。可以使用 `.env.local` 或当前终端环境变量：

```powershell
Copy-Item .env.example .env.local

# 或仅在当前 PowerShell 会话中设置
$env:DASHSCOPE_API_KEY="你的通义千问 Key"
$env:OPENAI_API_KEY="你的 OpenAI Key"
```

当前配置模板包含：

| Provider | 类型 | 说明 |
|----------|------|------|
| `mock` | 本地模拟 | 课堂演示和离线验证，最稳定 |
| `qwen` | OpenAI-compatible | DashScope 通义千问 Qwen-VL |
| `openai` | OpenAI-compatible | OpenAI 视觉模型配置 |
| `ollama` | OpenAI-compatible | 本地 Ollama 视觉模型 |

前端页面中手动输入的 API Key 只用于当前请求，不会保存到项目文件。

## 常用命令

### Mock 单场景调用

```powershell
py demo/vlm_call.py --mock-scene S02
```

### 重新生成 demo 场景和 mock 数据

```powershell
py demo/tools/generate_demo_assets.py
```

### 批量运行数据集

```powershell
py -m src.run_inspection --dataset demo --provider mock --prompt-id risk_inspection_v1
```

真实 Provider 示例：

```powershell
$env:DASHSCOPE_API_KEY="你的通义千问 Key"
py -m src.run_inspection --dataset demo --provider qwen --prompt-id risk_inspection_v2
```

### 查看历史 run

```powershell
py -m src.run_inspection --list-runs
```

## 数据与输出

项目把规则、样本、模型输出和评测结果分离管理：

```text
configs/
  risk_rules.json              # 风险规则统一来源
  providers.example.json       # Provider 配置模板
  prompts/                     # Prompt 版本
datasets/
  custom/                      # 自建样本和人工标注
  homesafe_like/               # 预留公开数据集转换目录
  behavior_like/
  esi_like/
outputs/
  vlm_results/                 # 每次巡检 run 的结果
  evaluations/                 # 自动评测和失败案例
  reports/                     # 报告输出预留目录
```

大体积自建图片、真实 API 输出和运行产物默认不会提交到 GitHub。仓库中只保留 `.gitkeep`、示例配置、课程 demo 数据和必要文档。

## 项目结构

```text
.
├── demo/                      # 课程演示前端和可离线数据
│   ├── index.html             # 静态闭环演示
│   ├── inspect.html           # 实时巡检
│   ├── annotate.html          # 自建样本标注
│   ├── batch.html             # 批量运行
│   ├── compare.html           # 多 run 对比
│   ├── data/                  # 场景、规则、mock VLM 输出
│   ├── assets/scenes/         # 12 个 SVG 虚拟室内场景
│   ├── prompts/               # demo Prompt
│   └── tools/                 # demo 数据生成脚本
├── src/
│   ├── datasets/              # 样本 schema 和加载器
│   ├── providers/             # VLM Provider 抽象和实现
│   ├── prompts/               # Prompt 构建器
│   ├── evaluation/            # 指标、失败案例和 run 对比
│   ├── reports/               # 报告生成预留模块
│   ├── run_inspection.py      # 批量巡检入口
│   └── server.py              # FastAPI 后端
├── configs/                   # 风险规则、Provider、Prompt 配置
├── datasets/                  # 自建或转换后的数据集
├── outputs/                   # VLM 结果、评测结果、报告
├── docs/                      # 课程文档和展示材料
├── game/                      # 游戏化巡检前端
├── tests/                     # 测试预留
├── AGENTS.md                  # 项目开发规范
├── requirements.txt           # Python 依赖
└── .env.example               # 环境变量模板
```

## 风险类别

当前 demo 覆盖 6 类室内安全风险，规则统一维护在 `configs/risk_rules.json`：

- 触电风险
- 火灾风险
- 绊倒风险
- 坠落风险
- 化学品风险
- 卫生/清洁风险

规则包含 `rule_id`、风险类型、触发条件、等级策略、正例和负例，可用于生成 Prompt、前端说明和评测逻辑。

## 评测关注点

课程展示时建议重点说明这些指标：

- 样本数、风险样本数、正常样本数
- 风险类别覆盖数
- 漏检数和误检数
- 风险类型匹配数
- 风险等级错误数
- 输出格式错误数
- 至少 3 个失败案例及原因分析

已有失败案例文档见 `docs/failure_cases.md`。

## 验证建议

每次改动后至少运行：

```powershell
py demo/vlm_call.py --mock-scene S02
py demo/tools/generate_demo_assets.py
```

如果使用本项目虚拟环境，也可以显式调用：

```powershell
.\.venv\Scripts\python.exe demo/vlm_call.py --mock-scene S02
.\.venv\Scripts\python.exe demo/tools/generate_demo_assets.py
```

## 安全与隐私

- 不要提交 `.env.local`、API Key、账号、cookie 或真实个人隐私照片。
- 真实宿舍、实验室照片应模糊人脸、姓名、学号、屏幕内容等敏感信息。
- 外部 API 调用前先确认图片内容适合上传到对应服务。
- 输出报告和运行结果不要包含密钥、完整私人路径或敏感信息。

## 后续计划

- 完成 HTML 或 Markdown 巡检报告生成。
- 增加更多真实自建样本和多视角样本。
- 完善 OpenAI、Gemini、custom HTTP Provider。
- 补充自动化测试和课程最终报告导出。
