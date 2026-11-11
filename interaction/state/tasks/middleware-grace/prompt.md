# 任务：远程访问中间件对 Brain 手机路径启用离线宽限

工作目录：/Users/prts/Projects/octopus-wt-auth-grace（分支 dev-auth-offline-grace，上一个提交 f3ad4d79 已实现注册路由的离线宽限，先读它的 diff：`git show f3ad4d79`）。只改这个 worktree，不要 commit / push。
跑测试：cd /Users/prts/Projects/octopus-wt-auth-grace/octopus && /Users/prts/Projects/octopus/octopus/.venv/bin/python -m pytest -q tests/router tests/channel_runtime tests/utils/test_remote_access_public.py

## 背景
远程访问开启时，公网请求先过 octopus/router/remote_access/middleware.py:remote_access_auth_middleware。手机（公网 IP）带 Second Brain bearer，中间件用 verify_access_token_identity（router/remote_access/auth_helpers.py）实时请求远端 /user/me；远端 503 时异常被吞，直接返回 401 login_required，请求到不了 f3ad4d79 的注册宽限。手机的请求都带头 `X-Channel-Id: brain`、`X-Instance-Id: <实例 id，如 ios-35F5C240-...>`。手机实际访问的路径：
- `POST /api/v1/register`
- `/api/v1/instances/brain___<实例id>/...`（上传 service/record、home-prompt 等）
- `/api/v1/channels/brain/instances/<实例id>/...`

## 要做的
1. instance_registry.py：把 `_offline_grace_identity` 改成公开方法 `offline_grace_identity`（保留同样规则；更新 f3ad4d79 里的内部调用和测试）。
2. 新增一个纯函数（放 channel_runtime 下合适的模块，如 instance_registry.py 或新的小模块）`brain_instance_id_for_remote_grace(path: str, method: str, headers) -> str | None`：
   - `/api/v1/instances/brain___<id>` 或其子路径 → 返回 path 中的 <id>（取 `brain___` 后、下一个 `/` 前）。
   - `/api/v1/channels/brain/instances/<id>` 或其子路径 → 返回 <id>。
   - `POST /api/v1/register`（只 POST）→ 返回 `X-Instance-Id` 头（去空白）；没有则 None。
   - 其他任何路径 → None（例如 /api/v1/notifications、/api/v1/profile/...、/ui、其他 channel 一律不放行）。
   - path 内 id 与 X-Instance-Id 头同时存在但不一致（大小写不敏感比较）→ None。
3. middleware.py：bearer 校验失败时，**只有**失败原因是「远端不可用」（httpx.TransportError，或 httpx.HTTPStatusError 且 status>=500；可复用 second_brain.auth 里的判定，必要时把它抽成公开函数 `is_auth_unavailable_error(exc)`）才尝试宽限：
   - 用上面的函数取 instance id；None 则照旧 401。
   - registry = get_brain_instance_registry()；device_uid_field 同注册路由；lookup_id = registry.find_existing_instance_lookup_id("", field, instance_id)；identity = registry.offline_grace_identity(lookup_id, bearer_token)。
   - identity 非 None：request.state.remote_session_identity = identity（含 offline_grace），call_next；logger.warning 记 path 前缀类别、lookup_id、grace_mode（不记 token/hash）。否则照旧 401。
   - 远端返回 401/403 等 4xx、assert_owner_identity 的 401/403 → 不宽限，行为不变。
   - assert_owner_identity 若因远端不可用抛异常（它可能调 resolve_discovery_identity），同样视为不可用；但若 verify_access_token_identity 已成功拿到身份且 owner 不匹配（403），不宽限。
   - 没有 bearer、session cookie 路径、白名单路径的行为完全不变。
4. 注册路由（mobile_compat_router.register_device）不改：中间件放行后它仍会做自己的宽限校验（用 body 的 device_uid / instance_id），两道都要过。

## 测试
- 纯函数：三类路径正确取 id；非 Brain 路径、GET /api/v1/register、无头的 register、path/头不一致 → None。
- 中间件（参考 tests/router/test_remote_access_auth.py 的构造方式，启用远程访问、模拟非本机请求）：
  - 远端 503 + 已知实例 legacy 记录 + Brain 上传路径 → 放行（下游 handler 被调用）。
  - 远端 503 + 非 Brain 路径（/api/v1/notifications）→ 401。
  - 远端 503 + 未知实例 → 401。
  - 远端 ConnectError → 同 503 处理。
  - 远端 401 → 401，不宽限。
  - 有 hash 的记录 + 不匹配 token → 401。
  - 远端正常 → 原路径不变。

## 文档
在 docs/mobile-pc-api-and-resource-protocol.md 的「Second Brain 认证离线宽限（过渡版）」一节补一段：远程访问中间件对上述三类 Brain 路径应用同一宽限规则，其他路径仍要求在线验证；以及 register 两道校验。

## 完成标准
上面三组测试全部通过（报告数量），汇报改动文件与取舍。
