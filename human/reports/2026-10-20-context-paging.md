# 把上下文当作内存：压缩 = 页面置换？

> 2026-10-20。你的问题：可以把上下文压缩类比为页面置换，用“去 memory 库取东西的次数”（缺页次数）来评价压缩算法吗？会出现 Belady 现象吗？

## 结论先行
1. **这个类比是成立的，而且已经有人做过。** MemGPT（2023）最早把上下文当作内存层级来管理。离你的设想最近的是 **Pichay**（2026-03，cs.OS）：它是一个代理层，负责逐出旧内容；模型重新请求被逐出的内容时，就记一次缺页；再根据缺页历史固定工作集。它在离线重放中统计缺页率，还观察到了抖动（thrashing）。所以“用缺页率评价置换策略”**这个思路本身不是新的**。
2. **但你的指标有一个漏洞**：硬件缺页一定会触发，**模型缺信息时却未必会去取**，它可能直接编造。如果只数“显式缺页”，就会奖励那些让模型连自己忘了什么都不知道的算法。这一点是可以做出新东西的地方：评价时必须把**隐式缺页**（因为缺信息而做错）也算进去。
3. **Belady 现象在 agent 里未必不可能**，只是会以“质量”的形式出现，而不是“缺页次数”。窗口越大，压缩发生得越晚，一次丢掉的内容也越多；再加上长上下文本身会让注意力变差（context rot）。这两点都可能让“窗口更大，结果更差”。这是一个可以证伪的假设，值得测。

## 类比对照
| 操作系统 | agent 上下文 | 类比是否成立 |
|---|---|---|
| 物理内存（帧） | 上下文窗口 | 成立 |
| 页 | 一段消息、工具输出、文件内容 | 部分成立：大小不等，而且可以被**有损压缩**成摘要（OS 没有“摘要页”） |
| 置换算法 | 压缩策略（清除旧工具输出 → 整段摘要） | 成立 |
| 缺页异常 | 重新读文件、查 memory、resume | **不对称**：不会自动触发，见结论 2 |
| 引用串 | agent 接下来要用到的信息 | **不对称**：模型看到什么，决定它下一步读什么，引用串依赖于算法本身，所以离线重放只是近似 |
| 工作集、抖动 | 当前任务需要的上下文；压缩后马上又读回来 | 成立：Claude Code 有专门的 “Autocompact is thrashing” 检测 |
| OPT / Belady | 理想上界；FIFO 的反常 | FIFO 不是栈算法，所以有 Belady 反常；LRU 和 OPT 是栈算法，没有。agent 版本见结论 3 |

## Baseline：两家现在怎么压缩
**Claude Code**（官方文档）：
- 接近上限时，先清除较早的工具输出，不够再整段摘要。触发点取决于模型，可以用 `/autocompact` 或 `autoCompactWindow` 调整（100K–1M）。
- 压缩后会从磁盘重新注入 CLAUDE.md、auto memory 和系统提示，重读最近修改过的至多 5 个文件，用过的 skill 也会带上限地重新注入。按路径生效的规则和子目录 CLAUDE.md 不会自动恢复。
- 可以用 `/compact <重点>` 或 CLAUDE.md 里的 “Compact Instructions” 控制摘要保留什么，也有 PreCompact、PostCompact hooks。
- 如果同一个大文件反复把窗口填满，会判定为抖动并停止重试。

**Codex**（源码 rust-v0.155.1，详见 LearnCodex/notes/01 §2、notes/03）：
- 默认在窗口的 90% 触发。
- 本地摘要保留最近的真实用户消息（约 2 万 token）和一条摘要；远端 V2 保留约 6.4 万 token 的用户消息和部分 agent 消息，再加上服务器生成的加密压缩块。
- 工具输出在写入历史时就会被截断。
- AGENTS 等宿主提供的上下文在压缩后重建。
- （notes/03 的补充见文末。）

两家的共同点：都是**“按类型 + 按新旧”的启发式**，类似 FIFO/LRU 加上固定页（pinned pages）。我还没看到任何一家按“这段内容将来还会不会被用到”来打分，这正对应 OPT 的思路。

## 可以做的实验（先离线，成本低）
1. **数据**：本机已有约 205MB 的 Codex rollout，加上 Claude Code 的 jsonl，都是真实工作轨迹。
2. **离线重放**：把每次读文件或命令输出当作一页，记录（路径、版本、token 数）。在不同窗口大小下模拟 FIFO、LRU、按类型、“只摘要”等策略，统计**显式缺页**：被逐出的页之后又被读取的次数。同时画出“窗口大小 → 缺页数”的曲线，看有没有 Belady 式的反常。
3. **在线（贵，后做）**：同一批任务、不同压缩设置，看隐式缺页，也就是验收失败、编造。这部分可以并入实验 E1 的工作包。
4. **评价指标**：显式缺页数 × 每次缺页的代价（token 和调用次数）+ 隐式错误率 + 总 token。

## 待你决定
- 是否先做离线重放？大约一两天的工程量，可以交给 Codex，数据都在本机。
- 这条线算 PRTS 的子课题，还是独立出来？它和 OS 课结合得很紧，适合做成一份课程报告或短文。

## 参考
- [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
- [The Missing Memory Hierarchy: Demand Paging for LLM Context Windows（Pichay）](https://arxiv.org/abs/2603.09023)
- [Virtual Context](https://virtual-context.com/paper/) · [AIOS](https://arxiv.org/abs/2403.16971) · [Cooperative Memory Paging with Keyword Bookmarks](https://arxiv.org/abs/2604.12376)
- Claude Code 文档：[Explore the context window](https://code.claude.com/docs/en/context-window) · [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) · [Troubleshooting](https://code.claude.com/docs/en/troubleshooting)
