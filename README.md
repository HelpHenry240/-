# AI 视觉室内巡检

一个面向室内安全图像的单次 VLM 巡检工具。当前版本只保留真实 API 接入流程：上传单图或同场景多视角图片，调用视觉模型，校验结构化结果，在原图中标注风险区域，在网页中渲染巡检报告，并导出 Markdown 或 PDF。

## 启动

需要 Python 3.10 或更高版本。

```powershell
python -m pip install -r requirements.txt
python -m src.server
```

打开 [http://localhost:8000/demo/index.html](http://localhost:8000/demo/index.html)。API 文档位于 [http://localhost:8000/docs](http://localhost:8000/docs)。静态打开 `demo/index.html` 也可以使用，但仍需启动后端服务。

## 模型 API

统一 Provider 使用 OpenAI-compatible `chat/completions` 多模态格式。页面可临时覆盖 Base URL、模型名称、额外请求头和请求体参数，因此除预设服务外，也能接入采用相同消息格式的代理网关或私有部署。

预设配置位于 `configs/providers.example.json`：

| Provider | 环境变量 | 默认用途 |
|---|---|---|
| 通义千问 / 百炼 | `DASHSCOPE_API_KEY` | Qwen-VL |
| 火山方舟 / 豆包 | `ARK_API_KEY` | 方舟视觉接入点 |
| 智谱开放平台 | `ZHIPU_API_KEY` | GLM 视觉模型 |
| 百度千帆 | `QIANFAN_API_KEY` | ERNIE 视觉模型 |
| 硅基流动 | `SILICONFLOW_API_KEY` | 托管开源视觉模型 |
| OpenAI | `OPENAI_API_KEY` | OpenAI 多模态模型 |
| Ollama | 无 | 本地视觉模型 |
| 自定义接口 | `CUSTOM_VLM_API_KEY` | 任意兼容服务 |

厂商模型名和可用地域会变化，以对应控制台为准。火山方舟通常需要把模型字段替换为实际推理接入点 ID。API Key 可以从环境变量读取，也可在网页中仅为本次请求临时输入；系统不会保存密钥、图片、模型结果或历史报告。

如需维护本地 Provider 配置，可复制示例文件：

```powershell
Copy-Item configs/providers.example.json configs/providers.json
```

`configs/providers.json` 仅保存 endpoint、模型名和环境变量名，不应包含密钥值。

## 报告接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/providers` | 查询可用 Provider |
| `GET` | `/api/prompts` | 查询 Prompt 模板 |
| `GET` | `/api/risk_rules` | 查询统一风险规则 |
| `POST` | `/api/inspect` | 上传图片、调用模型并返回结构化结果、Markdown 和渲染后 HTML |
| `POST` | `/api/reports/export` | 将当前报告导出为 `md` 或 `pdf` |

报告接口无状态，不创建历史记录。模型返回可靠的归一化 `bbox` 时，系统会在对应视角图片上绘制风险框，并嵌入相应风险条目的网页、Markdown 和 PDF 报告。PDF 导出使用 `reportlab`，会优先加载操作系统中的中文字体。

## 目录结构

```text
.
├── configs/
│   ├── prompts/indoor_safety_v1.md
│   ├── providers.example.json
│   └── risk_rules.json
├── demo/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── src/
│   ├── datasets/schema.py
│   ├── prompts/builder.py
│   ├── providers/
│   ├── reports/render.py
│   └── server.py
├── datasets/custom/          # 保留的用户自建图片，不由当前服务自动写入
├── docs/                     # 课程文档与展示材料
└── tests/
```

## 规则与 Prompt

`configs/risk_rules.json` 是风险定义的唯一来源。`PromptBuilder` 会把规则动态注入 `configs/prompts/indoor_safety_v1.md`，避免前端、Prompt 和后端各自维护一份规则。

当前覆盖触电、火灾、通行与绊倒、坠物、危险物暴露、燃气、漏水积水、卫生清洁八类风险。Prompt 明确约束证据充分性、排除条件、风险等级、归一化定位框和多视角证据编号。

## 验证

```powershell
python -m pytest
```

真实 API 调用会把图片发送到所选服务。上传含人脸、姓名、屏幕或其他隐私信息的图片前，请先脱敏并确认对应平台的数据处理政策。
