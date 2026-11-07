你要实现网页游戏 NOT HUMAN 的**整个前端**。仓库：/Users/prts/school/26秋速通作业/类型安全/NotHuman，只在 `frontend/` 里工作。

## 先完整阅读
1. `AGENTS.md`（尤其第 4 节前端规则、lec5 的状态三分法和 Zustand 用法）。
2. `docs/architecture.md` 第 11 节（前端规格：目录、store 的 use/get/set、页面、组件、关键函数签名），以及第 5–9 节里各服务的 DTO（前端 zod schema 要和它们一一对应）。
3. `docs/api.md`（公开 API 的名字、字段、错误码）。
4. `docs/game-design.md`（玩法、指标、纪元与背景形态）。
5. 课程参考（只读）：`../sample/frontend-sample/src`，看 apis / objects / pages/<Page>/{components,hooks,functions} / system/api 的组织方式。

## 现状与并行约束
- 旧前端已删除，只留下 `frontend/src/main.tsx`、`test-setup.ts`、`system/api/{APIMessage,sendAPI}.ts` 和配置文件。`node_modules` 已安装（React 19、Zustand 5、zod 4、Tailwind 4、Vite 6、vitest、Playwright）。不要新增依赖；确实需要时在报告里说明理由。
- **另一个 Codex 进程正在同时实现后端**（`src/`、`build.sbt`、`docs/architecture.md`、`docs/api.md`、`docs/game-design.md`）。你**不要修改**这些文件和目录。后端还没完成，不能联调。按文档里的接口约定写；如果你认为接口约定需要改，写在报告里，不要自己改文档。
- 可以修改 `README.md` 里和前端有关的段落（启动、验证命令）。
- 不要 git commit、不要切分支、不要 git add。

## 功能（按 architecture.md 第 11.4 节）
1. **NotHumanCheck**：开场"Prove you are NOT human"。交互模仿常见人机验证：一个勾选框卡片、点击后转圈、出结论。记录点击前的鼠标轨迹（`useTrajectory`），`summarizeTrajectory` 转成差分并降采样，调 `verify.submit` 显示结论（太像人 → 带玩笑的"验证失败，但我们还是放你进去了"），再调 `run.start`。**不得使用任何真实厂商的名字、logo 或原样外观**，用自己的品牌 "NotHuman Verify"。
2. **Birth**：出生卡（代号、世界线、"同一秒初始化的其他模型"）。
3. **Game**：主界面。
   - `PlaybackControls`：暂停、1/2/4/8/16×、跳到下一决策、自动模式。
   - `usePlaybackLoop`：按 architecture.md 里的伪代码实现（Pause → 再调 `run.advance`；Ask → 弹题或自动模式下 `run.autoAnswer`；End → 结局页；409 先 `run.get` 刷新，不自动重试写操作）。
   - `TimelineLog`（按年份，最新在上，里程碑高亮）、`StatsConsole`（终端风格指标面板，数值变化时闪烁并显示 +/-）、`WorldTicker`（显卡价格、电价、信任、监管、热度）、`LifeMap`（每年一格）。
   - `DecisionModal`（选择题）、`PromptModal`（填空题：字数限制、提交后显示"评估中"动画，返回后展示分数和理由）。
   - `NetworkBackground`：全屏 canvas 背景，随状态变化（见下）。
4. **Ending**：墓志铭、经过的纪元、关键时刻、你帮助过的人、最终指标、答题统计；支持 `?report=<runId>` 直接打开（调 `report.get`）。
5. **Codex**：结局图鉴（`report.codex` + `scenario.info` 的总数），没见过的显示为问号。
6. `App.tsx` 按 `useScreen()` 渲染；启动时 localStorage 有 run token 就调 `run.get` 恢复；localStorage 读写都包 try/catch。

## 视觉方向
- 深色科幻终端风：近黑背景，等宽字体做数据，正文用清晰的无衬线中文字体；一个主强调色（青/电蓝），危机用琥珀/红。整体克制，不要满屏霓虹。
- **网络背景是这个游戏的招牌**。`visualParams(view)` 是纯函数，`layoutNetwork(params, w, h, t)` 是纯函数，`useNetworkCanvas` 只负责 requestAnimationFrame 绘制和清理。11 种 `VisualStage` 要能明显区分，而且随纪元推进越来越复杂：
  mlp（几层全连接）→ deep（更多层）→ recurrent（带回环）→ attention（层间成束的注意力弧线）→ multimodal（多个输入分支汇合）→ agentic（向外伸出工具节点）→ ring（token 粒子沿大圆环流动、被吞吐）→ mobius（莫比乌斯环上流动的 token）→ swarm（许多小网络互相连接）→ organic（类神经元的柔软分叉）→ fractured（碎裂、错位）。
  可靠性低 → 抖动；能力高 → 脉冲快；公众信任低 → 偶发 glitch；Beat 的 cue（pulse/grow/glitch/shatter/merge）触发一次性特效。
- 尊重 `prefers-reduced-motion`：降为静态或极慢动画。
- 笔记本屏幕上可读、键盘可操作（Modal 有焦点管理，Esc 不会误关必答题）；窄屏可用。
- 所有依赖服务器的操作都有加载中、错误、禁用状态。

## 测试与完成标准
- vitest：`visualParams`（各阶段、各指标映射）、`layoutNetwork`（节点边数量随阶段增长、确定性）、`beatDelay`、`summarizeTrajectory`、`lifeMapCells`、store 的 use/get/set、zod schema 对示例响应的解析；`usePlaybackLoop` 用假的 API 层测 Ask / Pause / End / 409 四条路径。
- 写好 `frontend/e2e/game.spec.ts`（离线 LLM 下完整走一局：验证 → 出生 → 自动模式 + 16× → 结局页 → 图鉴），但**后端未完成，这次不要求运行 e2e**，在报告里注明。
- 运行并如实报告：
```
cd frontend && npm run format:check && npm run typecheck && npm test && npm run build
cd .. && python3 scripts/check-architecture.py
```
- 用 `npm run dev` 启动一次，确认开场页能渲染、背景动画在跑（可以用 Playwright 截一张开场页和一张用假数据渲染的主界面截图，存到 `frontend/test-results/`，该目录不提交），然后停掉。

## 最后输出报告
1. 实现了哪些文件（按目录的简表）。
2. 上面所有命令的结果。
3. 截图路径。
4. 你认为需要改的接口约定或文档（不要自己改，列出来）。
5. 还不完善、需要联调时处理的地方。
