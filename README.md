# AI 视觉室内巡检系统

基于 AI 视觉的虚拟室内巡检实践课程项目。目标是构建一个完整的室内安全巡检系统闭环：

```
构造室内场景 -> 生成风险样本 -> 调用 VLM 识别 -> 约束结构化输出 -> 形成巡检报告 -> 分析成功与失败案例
```

## 快速开始

### 1. 静态 Demo（无需安装，无需网络）

双击打开 `demo/index.html` 即可查看完整的静态演示：

- 12 个虚拟室内场景
- 6 类风险规则
- 人工标注 vs 模型输出对比
- 失败案例分析

### 2. 实时巡检（需启动后端）

#### 安装依赖

```powershell
pip install -r requirements.txt
```

#### 配置 API Key（可选）

复制 `.env.example` 为 `.env.local`，填入通义千问 API Key：

```powershell
Copy-Item .env.example .env.local
# 然后编辑 .env.local 填入 DASHSCOPE_API_KEY
```

获取地址：https://dashscope.console.aliyun.com/apiKey

也可以在启动时通过环境变量设置：

```powershell
$env:DASHSCOPE_API_KEY="你的Key"
```

#### 启动后端服务

```powershell
py -m src.server
```

服务启动后访问：

- 实时巡检页面：http://localhost:8000/demo/inspect.html
- 样本标注页面：http://localhost:8000/demo/annotate.html
- 静态 Demo：http://localhost:8000/demo/index.html
- API 文档：http://localhost:8000/docs

#### 使用实时巡检

1. 打开 http://localhost:8000/demo/inspect.html
2. 上传一张或多张同一场景的室内照片（JPG/PNG/SVG/WebP），可用于多视角巡检
3. 选择 Provider（mock 为本地模拟，qwen 为通义千问真实调用）
4. 如选择 qwen 且未配置环境变量，在页面输入 API Key
5. 点击「开始巡检」，查看结构化识别结果

> 即使没有网络和 API Key，也可以使用 Mock 模式演示完整流程。

### 3. 自建样本标注

启动后端后访问 http://localhost:8000/demo/annotate.html，可上传本地图片、框选风险区域、填写风险类型和等级，并保存到 `datasets/custom/annotations.json`。标注中的 `bbox` 使用归一化 `[x, y, width, height]`，可被前端热区展示和后续评测复用。

## 项目结构

```
.
├── demo/                    # 静态 Demo（最小可行演示）
│   ├── index.html           # Demo 展示入口
│   ├── inspect.html         # 实时巡检页面
│   ├── annotate.html        # 自建样本标注页面
│   ├── app.js               # Demo 交互逻辑
│   ├── inspect.js           # 实时巡检交互
│   ├── styles.css           # 页面样式
│   ├── data.js              # 前端加载的数据
│   ├── data/                # 风险规则、场景标注、mock 结果
│   ├── assets/scenes/       # 12 个 SVG 虚拟场景
│   ├── prompts/             # 巡检 Prompt
│   ├── vlm_call.py          # 命令行 VLM 调用入口
│   └── tools/               # 数据生成脚本
├── src/                     # 核心模块
│   ├── providers/           # VLM Provider 抽象（mock/qwen/openai/ollama）
│   ├── datasets/            # 数据 schema 与加载器
│   ├── prompts/             # Prompt 构建器
│   ├── evaluation/          # 批量评测、失败案例、run 对比
│   ├── reports/             # 报告生成（待实现）
│   └── server.py            # FastAPI 后端服务
├── configs/                 # 配置文件
│   ├── risk_rules.json      # 风险规则（唯一来源）
│   ├── providers.example.json  # Provider 配置模板
│   └── prompts/             # Prompt 模板
├── datasets/                # 数据集存储
├── outputs/                 # 输出结果
│   ├── vlm_results/         # VLM 调用结果
│   ├── reports/             # 巡检报告
│   └── evaluations/         # 评测结果
├── tests/                   # 测试
├── AGENTS.md                # 开发规范
├── requirements.txt         # Python 依赖
└── .env.example             # 环境变量模板
```

## 支持的 VLM Provider

| Provider | 类型 | 说明 |
|----------|------|------|
| mock | 本地模拟 | 无需网络和 API Key，用于课堂演示 |
| qwen | 云端 API | 通义千问 Qwen-VL，通过 DashScope 调用 |
| openai | 云端 API | OpenAI GPT-4.1-mini 等视觉模型 |
| ollama | 本地模型 | Qwen2.5-VL / LLaVA 等，需安装 Ollama |

Provider 配置见 `configs/providers.example.json`。复制为 `configs/providers.json` 可自定义。

## 命令行调用

```powershell
# Mock 模式
py demo/vlm_call.py --mock-scene S02

# 真实调用（需设置 API Key）
$env:DASHSCOPE_API_KEY="你的Key"
py demo/vlm_call.py --image path/to/image.jpg --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 --model qwen-vl-plus
```

## 开发计划

- [x] 阶段 A：数据 schema 稳定、src/ 骨架建立、风险规则抽离
- [x] 阶段 B：Provider 抽象、Qwen-VL 接入、单图/多图上传与实时巡检
- [x] 阶段 C：批量运行数据集、自动评测、失败案例筛选
- [ ] 阶段 D：多 Prompt / 多模型对比、课程报告生成

## 安全须知

- API Key 不会保存到服务器磁盘，仅用于当前请求
- 真实照片使用前应模糊人脸、姓名、学号等敏感信息
- 不要将 API Key 提交到 git 仓库
