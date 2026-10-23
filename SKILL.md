---
name: xuexitong-connector
version: 2.0.0
display_name: 学习通连接器接入助手
display_name_en: Xuexitong MCP Connector Setup
description: 一条命令把超星学习通接入 WorkBuddy：自动装服务端、配凭据、写连接器、跑自检，并在客户端信任后直接查课表、作业截止、考试、章节进度、通知与云盘。当用户说连接学习通、安装学习通 MCP、一键配置学习通、连接器里没有学习通工具、学习通登录失败、查学习通课表或作业 DDL 时使用。
description_zh: 一条命令把超星学习通接入 WorkBuddy：自动装服务端、配凭据、写连接器、跑自检，并在客户端信任后直接查课表、作业截止、考试、章节进度、通知与云盘。当用户说连接学习通、安装学习通 MCP、一键配置学习通、连接器里没有学习通工具、学习通登录失败、查学习通课表或作业 DDL 时使用。
description_en: One-command Xuexitong setup for WorkBuddy that installs the read-only MCP server, stores credentials, registers the connector and self-checks the result, then answers schedule, homework deadline, exam, progress, notice and cloud-drive queries.
---

# 学习通连接器接入助手

安装完这个 Skill，跑**一条命令**，剩下的交给它：查 Python、拉源码、装依赖、存凭据、写连接器配置、自检。你只需要在 WorkBuddy 里点一次「信任」。

## 功能范围

一条链路，六步自动化，一步人工：

| 步骤 | 做什么 | 自动化 |
|---|---|---|
| 1 | 检查 Python ≥ 3.10，确认解释器绝对路径 | 自动 |
| 2 | 定位服务端源码，缺失时 `git clone` 到 `~/.workbuddy/mcp-servers/xuexitong-mcp` | 自动 |
| 3 | `pip install -e .` 可编辑安装（这是能读到凭据文件的前提） | 自动 |
| 4 | 交互输入手机号与密码，写入 `config.json` 或 `mcp.json` 的 env | 自动 |
| 5 | 幂等写入 `mcp.json` 的 `mcpServers.xuexitong`，自动备份、回读校验 | 自动 |
| 6 | 跑 9 项体检：依赖、安装形态、凭据、登录态、条目、16 个工具 | 自动 |
| 7 | 在「连接器管理 → 自定义连接器」点**信任** | **人工，无法代劳** |

**不做**：签到、刷课、答题、批量爬取、成绩单统计。服务端本身只读。

可选加装：`--with-shortcut` 为本地学习通应用创建桌面快捷方式（.lnk），对应教学视频里「桌面连接器」的做法。

## 何时用 / 何时不用

**用**：连接学习通 / 装学习通 MCP / 一键配置 / 连接器里没有 `xuexitong` 工具 / 一直提示未登录 / 查课表与作业 DDL / 想给学习通应用做个桌面入口。

**不用**：只需要写作业或做 PPT（那是写作与 Office 技能）；学校自有教务系统（接口不通用）；任何自动化签到刷课需求。

## 前置条件

| 项 | 要求 |
|---|---|
| 客户端 | WorkBuddy 桌面版，有「自定义连接器」入口 |
| Python | 3.10+（脚本会自检） |
| git | 自动克隆源码时需要；没有则手动下载源码 |
| 账号 | 本人学习通手机号 + 密码（无扫码登录） |
| 网络 | 能访问 `*.chaoxing.com`、`*.cldisk.com`、`github.com` |
| 权限 | 全部写入都在用户目录，不需要管理员 |

## 一条命令接入

```bash
python scripts/setup.py
```

交互式跑完，最后打印唯一的人工步骤。常用变体：

```bash
python scripts/setup.py --phone 13800000000          # 只问密码（getpass 不回显）
python scripts/setup.py --credential-mode env        # 密码写进 mcp.json 的 env
python scripts/setup.py --no-clone                   # 已手动放好源码，不联网克隆
python scripts/setup.py --dry-run                    # 只打印计划，不落盘
python scripts/setup.py --with-shortcut "D:/学习/cxstudy/cxstudy.exe"   # 顺手建桌面入口
python scripts/setup.py --uninstall                  # 移除连接器条目
python scripts/setup.py --uninstall --purge          # 连凭据文件一起删
```

## 输入与配置项

| 参数 | 默认 | 说明 |
|---|---|---|
| `--phone` | 空，交互询问 | 学习通登录手机号 |
| 密码 | 空，`getpass` 交互 | 不接受命令行明文；非交互模式请用 `config.json` 预置 |
| `--credential-mode` | `config` | `config` 写入仓库根 `config.json`（推荐）；`env` 写入 `mcp.json` 的 env |
| `--server-dir` | `~/.workbuddy/mcp-servers/xuexitong-mcp` | 服务端源码位置 |
| `--config` | `~/.workbuddy/mcp.json` | 连接器配置文件 |
| `--force-credentials` | 关 | 忽略已有凭据，重新输入 |
| `--yes` / `-y` | 关 | 非交互模式，缺参直接失败而非卡住 |
| `--dry-run` | 关 | 全流程演练，不改任何文件 |

凭据优先级：服务端读取时是 `login` 参数 > 环境变量 > `config.json`；本脚本只写后两者，且把手机号一律掩码显示。

## 分步模式（脚本失败时的兜底）

```bash
# 1. 装服务端（-e 不可省，否则 config.json 落在 site-packages 读不到）
git clone https://github.com/DanMo661/Xuexitong-mcp.git
cd Xuexitong-mcp && python -m pip install -e .

# 2. 凭据
cp config.example.json config.json   # 填 phone / password

# 3. 写连接器
python scripts/register_mcp.py --python "C:/Python312/python.exe"

# 4. 体检
python scripts/check_env.py
```

## 可选：桌面入口

视频里那条「桌面学习通连接器」，本质是 `.lnk` 指向真实 exe 并固定工作目录：

```bash
python scripts/make_shortcut.py --target "D:/学习/cxstudy/cxstudy.exe" --name 学习通
python scripts/make_shortcut.py --verify-only --link "%USERPROFILE%\Desktop\学习通.lnk"
```

三级回退，任一条成功即返回：ctypes 直连 COM（无第三方依赖）→ pywin32 → PowerShell。每次写完都会**回读目标**比对，避免出现「图标对、目标错」的快捷方式。中文路径通过 `-EncodedCommand` 传递，不会变成乱码。

## 错误处理

脚本按「先取证、再给命令」的方式失败，不猜测：

| 症状 | 脚本行为 | 你要做的 |
|---|---|---|
| Python < 3.10 | 直接退出并打印当前版本 | 换 3.10+ 解释器重跑 |
| `git` 不存在 / 克隆失败 | 打印完整命令与 stderr 末尾 | 手动下载源码到 `--server-dir`，加 `--no-clone` 重跑 |
| pip 安装失败 | 打印可复制的 pip 命令 | 检查网络或代理后手动执行 |
| 缺手机号 / 密码 | 交互补问；`-y` 模式下直接失败 | 补 `--phone` 或在 `config.json` 预置 |
| `mcp.json` 不是合法 JSON | 中止，不覆盖、不「尽力修复」 | 修好 JSON 再跑 |
| 写入后回读不一致 | 报错并保留备份 | 用备份还原后排查磁盘/权限 |
| 自检有 FAIL | 打印 FAIL 明细与修复建议 | 按提示处理后重跑 |
| 自检有 WARN | 继续，但提示具体项 | 多数可忽略，如「登录态未生成」 |

**自检常见项**：`config.json 缺失` → 重新跑 Step 4；`普通安装` → 改用 `-e`；`command 不存在` → 用 `--python` 指定绝对路径；`工具数 < 16` → 升级服务端。

完整排查表见 [references/troubleshooting.md](references/troubleshooting.md)，按症状查的问答见 [references/faq.md](references/faq.md)。

## 校验标准

1. `python scripts/check_env.py` 无 `FAIL`。
2. `login` 返回「登录成功：你的名字」。
3. `get_profile` 返回真实姓名与学校。
4. `get_schedule` 与本学期实际选课一致。
5. 重启客户端后工具仍在。

## 安全边界

- **只读**：所有查询工具均为 GET 语义，不提交表单；不提供签到、刷课、答题。
- **凭据**：`config.json` 与 `session_cookies.json` 已在 `.gitignore` 中；POSIX 下写入后 chmod `0600`；密码不从命令行读取，日志一律掩码。
- **风控**：`get_homework_deadlines` 与 `get_progress_overview` 逐课扫描，一次约一分钟，别放进循环或短间隔定时任务。
- **仅限本人账号**，不共用会话文件。
- **接口非官方**：平台改版可能失效，此时升级服务端版本，不要改本仓库脚本绕过。

## 资源路由

| 文件 | 何时读 |
|---|---|
| `scripts/setup.py` | 一条命令接入（主路径） |
| `scripts/register_mcp.py` | 只重写/移除连接器条目 |
| `scripts/check_env.py` | 体检与排错第一步 |
| `scripts/make_shortcut.py` | 需要桌面快捷方式时 |
| `references/tools.md` | 16 个工具的参数、耗时、输出形态 |
| `references/troubleshooting.md` | 按症状排查 |
| `references/faq.md` | 「为什么必须信任」「密码存哪」「会不会封号」这类问题 |
| `SECURITY.md` | 信任边界与凭据落盘风险 |
| `tests/test_skill.py` | 改动仓库后跑 `python -m unittest discover -s tests -v` |
