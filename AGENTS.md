# AI 视觉室内巡检项目开发规范

## 1. 当前产品边界

项目当前只实现单次真实视觉模型 API 巡检闭环：

```text
上传单图或多视角图片 -> 调用 VLM API -> 校验结构化输出 -> 渲染巡检报告 -> 导出 MD/PDF
```

以下能力已经明确移除，后续不得在没有新需求的情况下恢复：

- 内置虚拟室内场景和默认模型输出。
- mock Provider 和无 API 的模拟巡检。
- 数据集批量巡检、自动评测和多 run 对比。
- 历史运行记录和历史评估报告。
- 网页样本标注与数据集管理。

`datasets/custom/` 中现有文件属于用户数据，只保留归档，不由当前服务读取或写入。

## 2. 核心约束

- API Key 只能从环境变量或当前请求读取，不得写入仓库、日志、响应或浏览器存储。
- 上传图片只允许写入系统临时目录，并在请求结束后删除。
- 巡检结果和报告保持无状态，不在服务端保存历史文件。
- 真实 API 调用失败时返回可读错误，但不得泄露请求头或密钥。
- Provider 默认采用 OpenAI-compatible 多模态 `chat/completions` 格式。
- 页面允许临时覆盖 Base URL、模型名、额外请求头和额外请求参数。
- 自定义参数不得覆盖核心 `model` 与 `messages` 字段。

## 3. 规则与 Prompt

`configs/risk_rules.json` 是风险规则唯一来源。每条规则至少包含：

- `rule_id`
- `risk_type`
- `risk_name`
- `description`
- `trigger_conditions`
- `exclusions`
- `level_policy`
- `positive_examples`
- `negative_examples`

`src/prompts/builder.py` 负责把规则注入 `configs/prompts/indoor_safety_v1.md`。不得在前端或 Python 业务代码中复制一份风险规则。

Prompt 必须约束：

- 只使用可见证据，禁止虚构距离、温度、气味、通电状态或不可见区域。
- 同时检查触发条件与排除条件，控制误报。
- 输出风险类型、规则编号、等级、依据、建议、定位框和多视角证据编号。
- 无风险时 `has_risk` 为 `false` 且 `risks` 为空。
- 证据不足时使用 `uncertain_points`，不得强行判定。

## 4. Provider 配置

示例配置维护在 `configs/providers.example.json`，本地覆盖文件使用 `configs/providers.json` 并由 Git 忽略。配置只能保存环境变量名，不能保存密钥值。

新增国内模型服务时，优先通过通用 OpenAI-compatible Provider 增加配置项。只有请求或响应结构确实不同，才新增独立 Provider，并保持统一的 `VLMProvider.inspect(images, prompt, options)` 接口。

厂商 endpoint、模型名和地域可能变化。修改预设时应核对厂商官方文档，并在描述中注明需要用户替换的接入点 ID 或工作空间信息。

## 5. 报告规范

- 网页默认展示渲染后的 HTML，不直接显示 Markdown 源码。
- Markdown 与 HTML 必须从同一份巡检数据生成。
- 模型提供可靠 `bbox` 时，应在 `primary_view_index` 对应图片上绘制风险框，并放在该风险条目中；不得为 `bbox: null` 的风险伪造标注。
- 导出接口只接受当前报告内容，支持 `md` 与 `pdf`，不保存文件。
- HTML 渲染必须转义模型内容，避免脚本注入。
- PDF 应优先使用系统中文字体；缺少 PDF 依赖时返回明确错误。
- 报告应包含模型、Prompt、输入文件、巡检结论、风险明细和证据充分性，不展示格式校验、结构化结果或原始 JSON。

## 6. 前端规范

前端是巡检工作台，不是营销页。唯一入口为 `demo/index.html`，应保持：

- 图片上传和多视角预览。
- Provider、Prompt、API Key、Base URL、模型名配置。
- 高级请求参数。
- 风险规则查看。
- 渲染后的报告结果。
- MD 与 PDF 导出。
- 明确的加载、错误、空状态与服务连接状态。

桌面与移动端均不得出现横向溢出、文字遮挡或控件重叠。

## 7. 验证

每次修改至少执行：

```powershell
python -m compileall -q src
python -m pytest -q
```

同时检查：

- `configs/*.json` 可解析。
- `demo/app.js` 语法正确。
- `/api/health`、`/api/providers`、`/api/prompts` 和 `/api/risk_rules` 正常。
- MD 与 PDF 导出的真实 HTTP 响应有效。
- 桌面和手机视口无横向滚动，浏览器控制台无错误。

真实模型验证需要用户提供有效 API Key。不得为了测试使用、提交或打印用户密钥。
