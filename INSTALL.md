# Claude 桌面版安装指南

## 1. 安装依赖

需要 Apple Silicon macOS、Node.js 20+、Homebrew Python 3.14，以及 Xcode Command Line Tools。

```bash
brew install python@3.14
scripts/bootstrap
```

在项目根目录执行。bootstrap 创建 `.venv`，安装 hash 固定的数据库和附件依赖、lockfile 固定的 Node 依赖，并运行测试。`LINE_RELAY_PYTHON` 可指定其他位置的 Python 3.14。默认不下载 Peekaboo；本 fork 默认只做本机快照刷新。不要将项目放在公开同步分享目录。

## 2. 指定个人 LINE 或分身

正常打开要读取的 App 并登录自己的账户；不需要发测试消息。

```bash
.venv/bin/python3 scripts/configure-claude.py --app '/Applications/仕事.app'
.venv/bin/python3 scripts/configure-claude.py --app '/Applications/仕事.app' --apply
```

应用路径是示例，可换成 `/Applications/LINE.app`。数据库自动发现范围限定在该 Bundle ID 的容器中。多个候选优先使用所选主进程实际打开的库；不能唯一确定时，用 `--db-file` 指定准确文件名。

预览不写配置。`--apply` 写入被 Git 忽略的 `runtime/line-target.json` 和 Claude 的 `claude_desktop_config.json`；原文件先私密备份，已有其他 MCP 连接保留。该步骤不获取密钥、不修改签名、不重启 LINE。

未配置目标就拒绝默认读取；已配置库缺失时也不会自动换另一个账户。已有配置不能直接覆盖成另一账户。当前 Keychain 服务只保存一个活动 LINE 数据库密钥，不支持多个账户并行的密钥隔离。

## 3. 查看状态

完全退出并重开 Claude，然后要求：

> 使用 work-line-readonly，执行 line_status。

`dbFound=true` 只说明数据库存在；需要同时 `keyAvailable=true` 和 `decryptOk=true` 才能读取。状态缺钥时不会自动提取。

## 4. 首次取密钥：显式调试扫描

如果已有有效密钥，请跳过本节。确认愿意承担短暂停顿或应用退出的可能性，再执行：

```bash
scripts/build-keychain-helper
.venv/bin/python3 scripts/capture-work-key.py --confirm-debug-scan
```

- 只附加 `runtime/line-target.json` 选定且正在运行的 App 主进程；身份变化或进程不唯一就拒绝。
- 不重新签名、不新建登录副本、不关闭系统保护、不调用发送操作，不使用 sudo。
- 优先扫描较小可写映射，总读取预算为 256 MiB，扫描时间预算 30 秒；符号加载、调试器附加和数据库验证可能另耗时。不是整个命令的严格总时限。
- 候选文件为 0600，私有目录为 0700；只有对所选账户快照认证成功的密钥才通过本机 helper 存入 Login Keychain。
- 候选、扫描状态和调试临时日志在命令结束时清除。不把密钥放入环境变量、命令行或文本配置。
- 扫描结束会请求 detach；调试异常可能使应用退出。权限拒绝、没有有效候选时停止；不要通过改签名或修改认证检查强行重试。

这是非官方接入，不保证不会触发平台限制。日常读取使用已存密钥，不需要每次扫描或调试。

## 5. 在 Claude 里读取

首次完成取钥后重启 Claude，先检查状态，再读取已知会话。

每次历史读取应依次调用：`line_status` → `refresh_latest` → `get_relationship_context` → `read_history`。服务在 MCP 初始化时把这一流程提供给 Claude，不需要安装其他 Agent 的技能。

`read_history` 单页最多 200 条。首次全面读取用 `order=oldest` 并跟随 `pagination.nextCursor`；后续增量按已有上下文游标继续，不能把一页当作完整历史。只需最近几条时可以用最新排序，但要明确查询范围。

同步状态始终按证据报告：默认 passive-only 不唤醒窗口，`localSnapshotRefreshed=true` 表示本机快照刷新，不能宣称服务器已全部同步。返回本次快照时间和目标会话最新本机消息时间。

## 排错

- Claude 看不到工具：完全退出重开；检查配置中的 Node 和项目入口绝对路径。
- `target_not_configured`：先运行配置脚本并 `--apply`。
- `db_target_missing`：检查所选账户是否搬迁或库名变化，不自动换库。
- `keychain_key_missing`：未配置密钥或钥匙串拒绝访问；不要贴出密钥。
- `no_valid_candidate`：扫描预算、版本或密钥存储形式可能不适用；不能推断数据库已损坏。
- 名称重名：确认候选 chatId，不自行猜测。
- 查不到老消息：只能读本机已有记录；按需补载历史是独立功能，不通过 OCR 或截图降级读取。
- 窗口激活组件无法编译：默认读取无需它。高级窗口功能需要兼容的完整 Xcode；不要为了解决编译问题切换未审查的 vendor 版本。

## 更新和迁移

已有使用中的安装目录，先备份私有状态，再检查 Git 工作树：

```bash
git pull --ff-only
scripts/bootstrap
```

更新后重启 Claude。若移动项目，在新目录重建依赖，再对同一 App 运行配置脚本；不要假设复制的 `.venv` 没有旧绝对路径。保留现有 data/runtime 与 Keychain 条目，未经本人决定不删除。

卸载先取消 Claude 中的 `work-line-readonly` 连接；密钥、本机记忆及缓存是否删除由本人决定。
