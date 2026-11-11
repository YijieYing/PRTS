# 任务：旧 Ear 录音素材全集索引（ear-baselines inventory）

仓库：/Users/prts/research/EchoAsRecord，分支 experiments/codex-baselines（工作区里已有未提交改动，属于本实验，保留，不要回滚、不要提交）。
先读：AGENTS.md、README.md（提交前检查命令）、experiments/codex_baselines/README.md、experiments/codex_baselines/ai-docs/implementation.md、services/adapters/src/ear_adapter/{source.py,readiness.py,ear_api.py}。

## 目的

负责人想知道「一共有哪些录音可以用来出题」。做一个只读盘点：列出所有能追溯到录音文件的素材，标明旧 Ear 的处理结果是否完整可用；没处理完或失败的，说明原因、能否重跑、怎么重跑。**不移动、不复制录音文件，不触发任何重跑或处理，不写旧 Ear 的数据库。**

## 数据来源（全部只读）

- 旧 Ear Evidence API：`EAR_ADAPTER_EAR_URL`（现在是 http://127.0.0.1:53980/internal）、`EAR_ADAPTER_EAR_TOKEN`，在 deploy/.env，用 `set -a && . deploy/.env && set +a` 加载。`GET /api/captures` 共 433 段；`GET /api/captures/{id}/evidence`。复用 ear_adapter 的 `HttpEarSource`、`InboxAudioLocator`、`readiness`。
- 旧 Ear 数据库（只读）：`~/.octopus/local/service/herryying30/octopus-service-ear/db/ear.sqlite3`。用 `sqlite3.connect("file:<绝对路径>?mode=ro", uri=True)`；有 pipeline_runs、pipeline_tasks、remote_jobs、audio_chunks、captures 等表。失败原因和「现在是否有任务在跑」从这里查。旧 Ear 源码在 `~/.octopus/local/servicehub/herryying30/octopus-service-ear/`（`ear/pipeline/`、`ear/api/routes_recordings.py` 的 reprocess、`routes_runs.py`、`routes_mvp.py` 的 analysis-rerun），用来理解状态字段和重跑方法。
- Brain inbox：`EAR_ADAPTER_DATA_ROOT`（默认 `~/.octopus/local`）下 `inbox/brain/{instance_id}/{日期}/{collection}/{HH-MM-SS}__{group_id}/`。也要找出 inbox 里有、但旧 Ear 不知道的音频文件（按 sha256 对照 captures 的 audio_ref）。

## 分类（每段录音一个 status）

- `ready`：旧 Ear 结果完整可用（`readiness` 判 Ready）且找得到音频文件。
- `processing`：现在仍有任务在排队或运行。
- `failed`：某阶段失败或卡住（含长时间不动的 running），写清楚阶段和原因（取数据库里的错误信息，归纳成人能读懂的一句话），以及 `rerunnable`（是/否/不确定）和 `rerun_how`（具体用旧 Ear 的哪个接口或命令、需要什么前提，比如远端 MOSS 要在线）。
- `incomplete`：没有失败记录，但结果缺某些部分（说明缺什么）。
- `audio_missing`：旧 Ear 有记录，但 inbox 里找不到音频。
- `not_ingested`：inbox 里有音频，旧 Ear 没有对应 capture。

分类规则以你在源码和数据里核实的为准；有拿不准的情况写进报告，不要硬归类。

## 输出

1. 代码：`experiments/codex_baselines/src/ear_baselines/inventory.py` + 命令行子命令 `ear-baselines inventory [--out DIR]`，默认输出到 `<EAR_BASELINES_ROOT>/inventory/`（默认 `~/.ear-baselines/inventory/`，在仓库外；真实数据不进仓库）。
2. `index.json`（给前端读，字段名照这个来，可以加字段，不要改名）：
   ```json
   {
     "generated_at": "ISO8601",
     "tz": "Asia/Shanghai",
     "totals": {"ready": 0, "processing": 0, "failed": 0, "incomplete": 0, "audio_missing": 0, "not_ingested": 0, "ready_hours": 0.0},
     "running_now": [{"capture_id": "...", "stage": "...", "since": "ISO8601"}],
     "failure_groups": [{"reason": "一句话", "count": 0, "rerunnable": "yes|no|unknown", "rerun_how": "..."}],
     "recordings": [{
       "id": "capture_id；not_ingested 用 file-<sha256 前 16 位>",
       "capture_id": "或 null",
       "status": "ready|processing|failed|incomplete|audio_missing|not_ingested",
       "started_at": "ISO8601，带 EAR_BASELINES_TZ 时区偏移（默认本机时区；本机是 Asia/Shanghai）",
       "local_date": "YYYY-MM-DD",
       "duration_s": 0.0,
       "audio_path": "绝对路径或 null",
       "audio_codec": "...",
       "counts": {"speech_segments": 0, "transcript_chars": 0, "speakers": 0, "audio_events": 0, "gps": 0, "phone_state": 0},
       "preview": "转写开头约 80 字，没有则空串",
       "failure": {"stage": "...", "reason": "...", "rerunnable": "yes|no|unknown", "rerun_how": "..."} 或 null,
       "missing": ["缺的部分"]
     }]
   }
   ```
   recordings 按 started_at 排序。时刻统一换算到显示时区（旧 Ear 有时返回 UTC，见 cases.display_tz）。
3. `index.md`：给人看的总览。开头是总数表、可用总时长、按日期的分布（每天几段、几小时）、现在在跑的任务；然后是失败原因分组表（原因、段数、能否重跑、怎么重跑）；然后按日期列出每段录音一行（时间、时长、状态、转写字数、预览、音频路径）。需要单行 front matter 吗？不需要，它在仓库外。
4. `transcripts/<id>.md`：每段 ready/incomplete 录音的时间线 Markdown，直接用已有的 `evidence_md.render_evidence`（显示时区）。后面出题和前端都会用到。

## 要求

- 433 段逐个读 evidence 会比较慢，可以并发（≤8）或缓存，但不要改旧 Ear。
- 单元测试放 `experiments/codex_baselines/tests/`，用 ear_adapter.testing 的合成数据和临时 sqlite，覆盖分类规则和 index.json 结构。不要在测试里访问真实旧 Ear。
- 更新 experiments/codex_baselines/README.md（用法里加 inventory）和 ai-docs/implementation.md（代码表、约定、验证记录）。不要改 reviewed-by / reviewed-at。
- 跑 README 的全部提交前检查（ruff、ruff format --check、pyright、pytest、tools/check_docs.py），都要通过。
- 最后在真实数据上跑一次 `uv run ear-baselines inventory`，确认输出。不要提交 git。

## 报告（写在最后一条消息里）

- 各状态的段数、可用总时长、日期范围。
- 失败原因分组：原因、段数、能否重跑、怎么重跑、需要的前提。
- 现在在跑的任务。
- 分类时拿不准的地方、与 ear_adapter.readiness 不一致的地方。
- 改了哪些文件、检查结果。
