已完成，修改仅留在指定 worktree，未 commit、未 push，未重启服务。

- `second_brain/auth.py`、`__init__.py`：新增并导出 `AuthUnavailableError`，保持默认调用行为。
- `instance_registry.py`：复用实例查找逻辑，保存 owner/hash，实现 7 天 hash 宽限和 14 天 legacy 宽限；离线注册不续期。
- `mobile_compat_router.py`、`legacy_instance_proxy.py`：接入 lookup_id，认证不可用映射为 503。
- 新增 `test_offline_auth_grace.py`，更新已有文档 `docs/mobile-pc-api-and-resource-protocol.md`。

测试结果：
- 新增 **64 项通过**；隔离数据目录后的相关模块 **131 项通过**。
- 指定全量命令被 **10 个收集错误**阻断。
- 继续执行可收集测试：**1342 通过、41 失败、10 跳过、10 错误**。41 个失败均在 HEAD 临时快照中复现，无新增失败项；因此尚未达到“全量通过”。

[全量测试日志](/tmp/octopus-auth-grace-pytest.log)