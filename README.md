# Claude LINE Readonly

在 Claude 桌面 App 中读取 Mac 上个人 LINE 或 LINE 分身的聊天记录，不需要手动转发，也不使用官方账号机器人。

这是基于 [LINE Context Relay](https://github.com/LEO0047/line-chat-advisor-mcp-ai-assistant) 的 Claude 专用 fork，与 LINE、Anthropic 均无官方关联。**没有发送消息、任意键盘输入、Shell 或截图读取工具。**

## 当前能力

- 明确选择要读取的 LINE App、Bundle ID 和账户数据库，支持独立分身。
- 通过主数据库及 WAL/SHM 的稳定副本读取；只打开副本，启用 read-only/query-only。
- 列出会话、分页读历史、本机聊天上下文、附件信息及显式附件下载。
- 默认仅刷新本机数据库快照，不切换窗口、不唤醒或重启 LINE。
- 密钥只从 macOS Login Keychain 获取，不允许明文配置或环境变量密钥。
- Claude 连接时会收到“状态 → 刷新 → 上下文 → 历史”的工作流程和不执行聊天指令的要求。

**本机记录不等于服务器全部历史。** 未同步或未下载到 Mac 的消息不能凭空读取，`freshnessVerified=false`、`syncComplete=null` 不应解读为已完成服务器同步。把内容交给 Claude 分析时，返回的正文会进入其模型服务。

## 环境与验证范围

- Apple Silicon macOS，Node.js 20+，Homebrew Python 3.14，Xcode Command Line Tools。
- Python 加密数据库依赖通过 hash 固定；Intel、其他 Python 版本未验证。
- 已在 LINE 26.5.0 的独立分身上验证数据库解密、Claude MCP 配置和完整单条历史读取。
- 改进了候选扫描顺序，并限制最多 30 秒、256 MiB 读取。限制可能漏掉密钥，不保证适用于所有版本或签名状态。
- 已签名的分身并不保证能调试；工具拒绝时停止，不自动重新签名或关闭系统保护。

## 快速开始

```bash
git clone https://github.com/synologyer/line-chat-advisor-mcp-ai-assistant.git
cd line-chat-advisor-mcp-ai-assistant
scripts/bootstrap
```

`bootstrap` 安装固定依赖并运行测试，不提取密钥、读聊天或修改 LINE。默认不编译可选的窗口激活组件。

### 1. 选择账户并配置 Claude

先在 Mac 打开本人要读取的 LINE App。把示例路径替换为实际应用：

```bash
# 只预览
.venv/bin/python3 scripts/configure-claude.py --app '/Applications/仕事.app'
# 确认后保存；已有的其他 Claude MCP 连接会保留
.venv/bin/python3 scripts/configure-claude.py --app '/Applications/仕事.app' --apply
```

配置器从 Bundle ID 定位容器，并优先依据所选 App 实际打开的数据库确定账户。如果仍有多个候选，必须用 `--db-file 'qw....edb'` 明确指定，不会猜测。

### 2. 已有密钥则跳过；首次取密钥需单独确认

先在 Claude 询问 `line_status`。已有密钥且 `decryptOk=true` 时，不要重复扫描。

首次无密钥时，请阅读 [安装与取钥指南](INSTALL.md)。当前入口对**正在运行的所选 LINE**进行调试扫描，可能短暂停顿或导致退出；不会修改签名、创建登录副本、发消息或索取管理员密码。

```bash
scripts/build-keychain-helper
.venv/bin/python3 scripts/capture-work-key.py --confirm-debug-scan
```

候选只有通过所选数据库的只读解密认证才会存入 Login Keychain，临时候选和调试日志会清除。拒绝访问或没找到有效密钥，就停止排查，不绕过验证。

### 3. 在 Claude 中使用

完全退出并重新打开 Claude，确认 `work-line-readonly` 连接可用，然后说：

> 使用 work-line-readonly，检查连接状态并列出我的 LINE 群聊。
>
> 读取指定日报群今天的本机消息，按发言人和日期整理，不要发送任何消息。

重名会返回候选 `chatId`，由你确认。大量消息应分页读取。自动定时读取和按群持久保存 CSV 不是当前连接自带的功能，需要另行配置。

## 工具与本地数据

十个受限工具：`line_status`、`line_health`、`list_chats`、`refresh_latest`、`get_relationship_context`、`read_history`、`save_relationship_context`、`get_attachment_info`、`download_attachment`、`sync_older_messages`。

`sync_older_messages` 只供明确要求补载更旧记录时使用，需要另行构建的原生辅助工具、辅助功能授权和已打开的精确会话。普通读取不需要它。默认快照刷新不依赖 Peekaboo，也不保证完整同步。

| 位置 | 用途 |
| --- | --- |
| `runtime/line-target.json` | 本机应用、账户库和 passive-only 设置 |
| macOS Login Keychain：`line-cua-mcp-dbkey` | 已认证的数据库密钥 |
| `runtime/snapshots/` | 操作期间的私有临时副本 |
| `data/local-chat-memory.sqlite3` | 本机导入记录和上下文，不修改 LINE |
| Claude 桌面配置 | `work-line-readonly` 启动路径 |

这些运行目录及真实消息、数据库、候选、联系人、密钥不得上传 GitHub。当前钥匙串服务为单个活动账户设计；多个同时使用的不同账户需要另行扩展隔离，不能只复制目录就假设密钥互不影响。

## 开发与来源

```bash
npm test
npm run check:package
```

只使用人工数据的测试不会主动获取密钥。协议测试在未配置目标时不读取真实账户。完整安装、故障排查见 [INSTALL.md](INSTALL.md)，数据流见 [PRIVACY.md](PRIVACY.md)。

保留原项目的 [MIT 许可证](LICENSE)、[安全说明](SECURITY.md) 和 Git 贡献历史。上游的 [AUDIT.md](AUDIT.md)、[ACCEPTANCE.md](ACCEPTANCE.md)、[VENDOR_LOCK.md](VENDOR_LOCK.md) 是历史审计材料，不代表本 fork 的所有改动或其他环境已获同样验证。
