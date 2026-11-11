# 任务：Brain 手机注册在 Second Brain 认证服务宕机时离线放行（过渡版）

工作目录：/Users/prts/Projects/octopus-wt-auth-grace（git worktree，分支 dev-auth-offline-grace，基于 origin/dev）。只改这个 worktree，不要碰 /Users/prts/Projects/octopus。不要 commit，不要 push，改完留在工作区，我来审查。
跑测试：cd /Users/prts/Projects/octopus-wt-auth-grace/octopus && /Users/prts/Projects/octopus/octopus/.venv/bin/python -m pytest -q tests
（用主 checkout 的 venv；从 worktree 的 octopus/ 目录运行时 import 的是 worktree 代码）

## 背景
远端 Second Brain（SECOND_BRAIN_API_BASE_URL，http://brain.shiweinan.com:31000/api/v1）从 2026-11-07 起 /user/me 返回 503 "no available server"、间歇 DNS 失败。
手机 Brain App 调 `POST /api/v1/register`（octopus/channel_runtime/mobile_compat_router.py:register_device，self_register 模式），走 `BrainInstanceRegistry.validate_self_registration_token`（octopus/channel_runtime/instance_registry.py），它要远端 /user/me 验 discovery 身份和 bearer 身份；远端挂了就 ValueError → 401。手机每 12s 重试，全部 401，录音停传。
注册成功后上传用本地 service_token 校验，不依赖远端。所以只需让「已验证过的那台手机」在远端不可用时能注册/直连。

## 要做的
1. octopus/second_brain/auth.py
   - 新增 `class AuthUnavailableError(RuntimeError)`，从 second_brain/__init__.py 导出。
   - 判定「不可用」：httpx.HTTPStatusError 且 status >= 500；httpx.TransportError（连接失败、DNS、超时、Server disconnected 等）。401/403/其他 4xx 不算不可用。
   - `resolve_discovery_identity` 加关键字参数 `raise_unavailable: bool = False`。为 True 时：bearer 路径、access 路径、refresh 路径遇到「不可用」抛 AuthUnavailableError（chain 原异常）；其余行为不变。默认 False 时所有现有调用方行为完全不变（它们仍返回 None / 原样抛）。
2. octopus/channel_runtime/instance_registry.py
   - 抽 helper `find_existing_instance_lookup_id(device_uid: str, device_uid_field: str, requested_instance_id: str | None) -> str | None`，复用 register_instance 里「按 device_uid 找，找不到再按 requested_instance_id 的 slug lookup」的逻辑，register_instance 改为调用它（行为不变）。
   - `validate_self_registration_token(self, token, *, lookup_id: str | None = None)`：
     - 远端调用都用 raise_unavailable=True。
     - 远端成功（现有逻辑通过）时：返回的 identity 额外带 `"verified_token_hash": self._registration_token_hash(token)`；并把 owner 身份（user_id、user_name、verified_at）持久化到本地文件（放在 brain instances 目录同级，例如 instances 目录的父目录下 `owner_identity.json`；用现有路径计算方式，不要硬编码 ~/.octopus）。
     - 远端抛 AuthUnavailableError（discovery 或 bearer 任一步）时：调用 `_offline_grace_identity(lookup_id, token)`，通过则返回其结果，否则抛 AuthUnavailableError。
   - `_offline_grace_identity(lookup_id, token)` 规则（全部满足才放行）：
     a. lookup_id 非空且有实例配置；registration.mode == self_register；registration.auth.type == system_bearer；auth.verified_user_id 非空。
     b. owner：若本地 owner_identity.json 存在，其 user_id 必须 == auth.verified_user_id；若不存在（过渡），跳过这一条。
     c. 若 auth.verified_token_hash 存在：必须 hmac.compare_digest 等于 sha256(token)，且 auth.verified_at 距今 ≤ 7 天（常量 OFFLINE_GRACE_DAYS = 7）。返回 grace_mode="token_hash"。
     d. 若 auth.verified_token_hash 不存在（过渡，旧记录）：auth.verified_at 距今 ≤ 14 天（常量 OFFLINE_GRACE_LEGACY_DAYS = 14）即放行。返回 grace_mode="legacy_device"。
     e. 返回 {"user_id": verified_user_id, "user_name": auth.verified_user_name, "offline_grace": grace_mode}；打 logger.warning（含 lookup_id、grace_mode，绝不打印 token 或 hash）。
   - `_apply_registration_auth_state`：
     - 正常验证：在现有字段外写 `verified_token_hash`（来自 identity）。
     - identity 带 offline_grace 时：**不改** verified_at / verified_token_hash / verified_user_*，只写 `offline_grace_at`（now iso）和 `offline_grace_mode`。这样宽限期不会被自己续期，远端恢复后下一次正常注册会写入新 hash 并收紧。
   - `authorize_instance_access` 调 validate 时传 lookup_id。
3. octopus/channel_runtime/mobile_compat_router.py：register_device 在 self_register 分支先用 helper 算出现有 lookup_id 传给 validate；捕获 AuthUnavailableError → HTTPException(503, "Second Brain auth unavailable")。PermissionError→403、ValueError→401 保持。
4. octopus/channel_runtime/legacy_instance_proxy.py 第 ~53 行调用 authorize_instance_access 处：AuthUnavailableError 映射为 503（看现有异常映射风格）。

## 测试（新文件 octopus/tests/channel_runtime/test_offline_auth_grace.py，全部离线，用 httpx.MockTransport 或 monkeypatch，tmp_path 隔离路径；参考 tests/channel_runtime/test_mobile_compat.py 的 registry 构造方式）
- resolve_discovery_identity 默认参数下 503 仍返回 None（旧调用方不受影响）；raise_unavailable=True 时 503 / ConnectError 抛 AuthUnavailableError；401 不抛该异常。
- 远端正常：注册成功并在配置里存下 verified_token_hash、owner_identity.json。
- 远端 503 + hash 匹配 + 7 天内 → 放行，offline_grace_at 写入，verified_at/hash 未变。
- 远端 503 + hash 不匹配 → 503；超过 7 天 → 503。
- 远端 503 + 旧记录无 hash + 14 天内 → 放行（legacy_device）；超过 14 天 → 503。
- 远端 503 + 未知设备（无现有实例）→ 503。
- owner_identity.json 存在且 user_id 不同 → 503。
- 远端 401 → 401，不走宽限。
- authorize_instance_access 用 system bearer、远端 503、hash 匹配 → 放行。
- 通过 TestClient 打 POST /api/v1/register 至少覆盖 503 与宽限放行两条。

## 文档
在仓库里 grep `self_register`、`register`、`Second Brain` 相关文档（docs/、octopus/README.md、AGENTS.md 等），把离线宽限行为写进已有的、讲注册/认证的文档；没有合适的就在汇报里说明，不要新建大文档。

## 完成标准
全量 pytest 通过（报告通过/失败数）；汇报改了哪些文件、设计取舍、更新了哪些文档。
