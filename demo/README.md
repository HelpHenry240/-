# AI 视觉室内巡检 Demo

这是一个按照课程任务做的最小闭环 demo，包含：

- 12 个虚拟室内场景样本
- 6 类风险规则
- 人工标注
- 模拟 VLM 结构化输出
- 成功/失败案例对比
- 可选真实 VLM 调用脚本

## 直接演示

双击打开：

```text
demo/index.html
```

页面可以展示场景、人工标注、模拟 VLM 输出、识别对比和失败案例。

## 重新生成样本

```powershell
python .\demo\tools\generate_demo_assets.py
```

会重新生成：

- `demo/assets/scenes/*.svg`
- `demo/data/scenes.json`
- `demo/data/risk_rules.json`
- `demo/data/mock_vlm_results.json`
- `demo/data.js`

## 调用模拟结果

```powershell
python .\demo\vlm_call.py --mock-scene S02
```

## 接入真实 VLM

建议先把自己的真实照片或 PNG/JPG 场景图放到 `demo/assets/real/`。然后设置 API Key：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
python .\demo\vlm_call.py --image .\demo\assets\real\sample.jpg --output .\demo\outputs\sample_result.json
```

如果使用其他兼容 OpenAI Responses API 的服务，可指定：

```powershell
$env:VLM_API_KEY="你的 API Key"
$env:VLM_BASE_URL="https://你的服务地址/v1"
$env:VLM_MODEL="你的视觉模型名"
python .\demo\vlm_call.py --image .\demo\assets\real\sample.jpg
```

## 后续可以扩展

- 把 SVG 示例替换成真实照片或 AI 生成图
- 增加多视角输入
- 比较不同 Prompt 的输出稳定性
- 统计漏检、误检、等级错误
- 用 Streamlit 或 Gradio 做上传图片版本
