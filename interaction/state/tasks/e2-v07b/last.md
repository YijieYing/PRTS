已提交 `0581a4f`（`E2:`）。
[官方核实](https://api-docs.deepseek.com/guides/thinking_mode/)：temperature 无效，不能保证确定性；top_p 在 0.95–1.0 内有效。
带 tools 时，轮内及跨轮均须回传全部 reasoning_content，并计入 W；无 tools 不回传。
预算中位数情景：高峰 **$49.82 / ¥358.74**；错峰 **$24.91 / ¥179.37**（汇率7.20）。
含 recall 次数/输入上限：高峰 $78.94 / ¥568.35；错峰 $39.47 / ¥284.18；均为偏低经验估计。
**188 项测试通过**；未调用 DeepSeek、未执行 Codex 判分、未读写 `.env`。