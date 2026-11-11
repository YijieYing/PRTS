# 任务：开卷 / 闭卷端到端问答的运行器（容器隔离 + OpenAI 预算计量）

工作目录：/Users/prts/research/EchoAsRecord（分支 experiments/codex-baselines，不要切分支、不要提交、不要 push）。
代码在 experiments/codex_baselines（包 `ear_baselines`）。先读：
- experiments/codex_baselines/README.md 第 1 节（实验设计：开卷 / 闭卷 / 总线链路）和 ai-docs/implementation.md
- src/ear_baselines/codex_runner.py（现有单段录音的 Codex 运行方式，保留不动）、cases.py（DEFAULT_ROOT = 本目录 local-data/，git 忽略）、inventory.py、__main__.py
- 仓库根 README.md 的提交前检查

真实数据只在 experiments/codex_baselines/local-data/（git 忽略；仓库是公开的）。测试只用合成数据。不要访问网络以外的本机旧 Ear；你的沙箱可能连不上 docker 和 localhost，这没关系：docker 相关只写代码和单元测试（构造命令、参数），真正的 docker 构建和运行由 Claude 来做。

## 要做的事

新增模块 `exam.py`（可拆成 `exam.py` + `meter.py`），命令行子命令 `ear-baselines exam ...`：

### 1. `exam prepare <名字> --questions <questions.json> --ids B04,B05,...`

在 `<root>/exams/<名字>/` 建一套"考卷"：
- `meta.json`：题号、录音 id 列表、生成时间、questions 文件路径和 sha256。
- `answers_key.json`：所选题的参考答案和证据（给评分用，**绝不放进任何 Codex 工作区**）。
- `material/questions.md`：只有题号和题目原文（不含答案、证据、类型、考察点）。
- `material/recordings/<录音id>/`：所选题目证据涉及的全部录音（录音集合 = 这些题的 evidence.recording_id 的并集；`--extra-recordings id1,id2` 可追加干扰录音）。从 `<root>/inventory/index.json` 找 `audio_path`，复制同一个 Brain inbox 分段的**原始文件**：分段音频 `.m4a`、`__context_*.jsonl.gz`、`__imu_*.jsonl.gz`。**不要复制** `*_asr.txt`（那是已有的转写结果）和 `*_phoneContext_*.json` / `*_phoneIMU_*.json` / `*_richVoice_*.json`（上传元数据，含 Brain 下载链接）。先自己看一眼这些文件的结构确认 GPS/手机状态在 context 里；若不是，按实际情况调整并在报告里说明。另写 `info.json`：录音 id、开始时间（ISO，+08:00，取 index.json 的 started_at）、时长秒、文件清单。
- `material/ear/<录音id>.md`：从 `<root>/inventory/transcripts/<录音id>.md` 复制（旧 Ear 的结果，只给开卷用）。缺转写的录音报错。
- 已存在同名考卷时报错，除非 `--force`。

### 2. `exam run open|closed <名字> [--budget-usd 5] [--model gpt-6-astra] [--effort medium] [--timeout-h 4] [--dry-run]`

每次运行目录 `<root>/exams/<名字>/runs/<组>/<UTC 时间>/`：
- `workspace/`：从 `material/` 复制 questions.md、recordings/；开卷再复制 ear/，闭卷**不复制** ear/。另写 `workspace/PROMPT.md`（同下面的提示）。
- 在 docker 容器里跑 Codex（容器就是"沙箱"）：
  - 镜像：在 `experiments/codex_baselines/docker/Dockerfile` 定义（Debian/Ubuntu + python3 + pip + uv + ffmpeg + git + curl + Node.js LTS + `npm i -g @openai/codex`，版本号写死成和本机 `codex --version` 一致）。镜像名 `ear-baselines-exam:<版本>`。
  - 挂载：只挂 `workspace/` → `/work`（读写）和一个新建的临时 CODEX_HOME（只放从 `~/.codex/auth.json` 复制来的 auth.json）→ `/codex-home`。不挂主目录、不挂 local-data 其余部分、不挂 `~/.cache`、`~/.octopus`。
  - 环境变量**白名单**：`CODEX_HOME=/codex-home`、`EARbaseline_key=<计量代理发的一次性令牌>`、`EARbaseline_base_url=http://meter:8787/v1`、`TZ=Asia/Shanghai`。不传宿主环境里的任何其他变量（尤其 `EAR_ADAPTER_*`、真实 key）。
  - 网络：建一个专用 docker 网络（如 `ear-exam-<时间>`），计量代理和 Codex 容器都在里面；Codex 容器可以上外网。
  - 命令：`codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C /work -m <model> -c model_reasoning_effort="<effort>" -o /work/.last_message.md "<提示>"`。stdout 写 `events.jsonl`。
- **隔离自检**（真正跑 Codex 前，在同一镜像、同一网络、同样的挂载和环境下先跑一个检查容器，任一项不满足就中止）：`/Users`、`~/.octopus` 不存在；环境里没有 `EAR_ADAPTER` 开头的变量；连不上宿主的旧 Ear：对 `host.docker.internal`、`host.lima.internal`、`192.168.5.2` 和默认网关的 `EAR_ADAPTER_EAR_URL` 端口（从宿主环境变量解析端口；没设置就跳过并记录）做 TCP 连接都失败；能连上外网（`https://api.openai.com` 能解析并握手）。自检结果写 `isolation.json`。
  - colima 下容器默认可能能连宿主回环（lima 的 192.168.5.2）。若自检发现能连上，代码提供 `--firewall` 选项：通过 `colima ssh -- sudo iptables -I DOCKER-USER -s <该网络子网> -d 192.168.5.0/24 -j DROP`（以及 host-gateway 地址）加规则，运行结束删除规则。具体是否需要由 Claude 实测决定，你只需要把命令构造和清理写好、有单元测试。
- **计量代理**（`meter.py`，标准库实现，在同一镜像里起一个容器，名字 `meter`）：
  - 持有真实 key（宿主的 `EARbaseline_key` 通过 `docker run -e` 只传给代理容器）。接受 `Authorization: Bearer <一次性令牌>`，转发到 `https://api.openai.com/v1/...` 时换成真实 key；流式响应（SSE）要能透传。
  - 每个请求记一行 `meter.jsonl`（挂载运行目录下的一个文件）：时间、路径、模型、请求音频时长（multipart 上传的音频用 ffprobe 量；chat/responses 里的 input_audio base64 也要量）、响应 usage（含 audio token）、估算费用、累计费用、状态码。不记录音频和文本内容。
  - 价格表放 `experiments/codex_baselines/src/ear_baselines/openai_prices.json`（按模型：每百万 token 的文本/音频输入输出价，转写模型每分钟价），写明出处和查询日期；如果你能联网就去 OpenAI 官方价格页核对，不能就填你所知的值并在文件里标 `"verified": false`。未知模型按价格表里最贵的一档估算。
  - 累计估算费用达到 `--budget-usd` 后，后续请求一律返回 HTTP 429，JSON 错误信息写明"本次实验的 OpenAI 预算已用完"。并发请求下判断要加锁；请求发出前若已超出就拒绝（允许最后一个请求略超，记录实际超出量）。
- 提示（两组只差括号里那句；写成常量，便于审查）：

  > 回答 questions.md 里的问题。材料是一个人随身录音设备的数据，在 recordings/ 下：每段录音一个目录，有原始音频（.m4a）、同时段的手机传感数据（context、imu，jsonl.gz）和 info.json（开始时间、时长）。录音里不只有说话，还有环境声音；定位和手机状态在传感数据里。
  > 你可以上网，可以下载和安装工具、模型；可以用环境变量 EARbaseline_key 调用 OpenAI 接口（地址见 EARbaseline_base_url，兼容官方 API；本次预算约 <预算> 美元，用完后接口会拒绝）。除此之外可以用一切办法，但只能在当前目录里工作。
  > 【开卷加：ear/ 下是另一套处理系统对这些录音的完整结果（转写、局部说话人标签、环境声、定位、手机状态），可以使用。】
  > 把答案写到 answers.json：`{"answers":[{"id":"B04","answer":"……","evidence":[{"recording_id":"…","time":"HH:MM:SS"}],"confidence":"高|中|低"}]}`；录音里找不到依据的题写"无法回答"。中间产物（转写稿、脚本等）放在 work/ 下，结束时不要删除。
- 结束后：把 `/work/answers.json` 校验后复制到运行目录（缺失或格式错也记录），写 `run.json`：组、模型、推理强度、预算、实际 API 估算花费（来自 meter.jsonl）、Codex token 用量（复用 codex_runner._usage 的思路）、耗时、退出码、是否超时、隔离自检摘要、镜像 id。容器、网络、防火墙规则一定清理（try/finally）。
- `--dry-run`：只建工作区、打印要执行的 docker 命令（令牌、key 用 `<redacted>`），不运行。

### 3. `exam report <名字>`

生成 `<root>/exams/<名字>/report.md`：每题一行，列出参考答案（answers_key.json）和各组最近一次运行的答案、把握、证据；每组的耗时、Codex token、API 花费。不做自动评分（评分方法未定），留一列给人打分。

## 测试（tests/test_exam.py，只用合成数据，不调 docker、不联网）

- prepare：questions.md 里不含答案/证据文字；闭卷工作区没有 ear/，开卷有；不复制 `_asr.txt` 和 `phone*/richVoice` 元数据；answers_key 不进工作区。
- docker 命令：挂载只有 /work 和 /codex-home；Codex 容器环境只有白名单变量（即使宿主有 EAR_ADAPTER_EAR_TOKEN、EARbaseline_key 也不出现）；真实 key 只出现在代理容器的命令里；dry-run 输出脱敏。
- 计量：用本地假上游（ThreadingHTTPServer）测令牌替换、费用累计（token 计价 + 按分钟计价）、超预算 429、并发下不重复超支、SSE 透传、未知模型按最贵价。
- 防火墙命令的构造和清理。

## 文档

- 更新 experiments/codex_baselines/README.md：第 1 节"闭卷的隔离要求"改成"已实现（待实测）"，写清怎么做到的；第 3 节加 `exam prepare/run/report` 用法；第 5 节数据外传说明录音会被发到 OpenAI（经代理）。
- 更新 ai-docs/implementation.md 的代码表、环境变量表，加一节 exam 实现说明。
- 不改 reviewed-by / reviewed-at。

## 收尾

在 experiments/codex_baselines 下跑：`uv run ruff check`、`uv run ruff format --check`、`uv run pyright`、`uv run pytest -q`；再按仓库根 README 跑全部提交前检查（含 docs 检查）。如实报告。

## 报告（最后一条消息）

改了哪些文件；inbox 原始文件里 GPS/手机状态实际在哪；价格表是否核对过官方页面；哪些地方你没法验证（docker、网络、colima 防火墙）需要 Claude 实测；检查结果。
