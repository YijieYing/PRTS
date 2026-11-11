已完成，仅修改当前 worktree，未 commit / push。

- `instance_registry.py`：公开 `offline_grace_identity`，新增三类 Brain 路径解析及头部一致性检查。
- `middleware.py`、`owner.py`、`second_brain/auth.py`：仅远端不可用时尝试宽限；owner 查询支持按需透传故障，4xx 和身份不匹配不放行。注册路由未改。
- 更新两份认证测试；另修复 `test_mobile_compat.py`、`test_setup_router.py` 的目录隔离和真实凭据依赖。
- 更新 `docs/mobile-pc-api-and-resource-protocol.md`，说明路径范围与 register 两道校验。

指定三组测试：**166 passed**。`git diff --check` 通过。

已尝试执行重启脚本，但因无法取得 `~/.octopus/local/logs/octopus.start.lock.d` 启动锁而失败，未验证运行中服务。