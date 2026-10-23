---
name: xuexitong-connector
version: 1.1.0
display_name: 学习通连接器接入助手
display_name_en: Xuexitong MCP Connector Setup
description: 把超星学习通以自定义 MCP 连接器接入 WorkBuddy 并完成登录验证，随后用只读工具查询课表、作业截止、考试、章节进度、通知与云盘。当用户说连接学习通、安装学习通 MCP、连接器里没有学习通工具、学习通登录失败、查学习通课表或作业 DDL 时使用。
description_zh: 把超星学习通以自定义 MCP 连接器接入 WorkBuddy 并完成登录验证，随后用只读工具查询课表、作业截止、考试、章节进度、通知与云盘。当用户说连接学习通、安装学习通 MCP、连接器里没有学习通工具、学习通登录失败、查学习通课表或作业 DDL 时使用。
description_en: Connect Chaoxing Xuexitong to WorkBuddy as a custom MCP connector, complete login, then run read-only queries for schedule, homework deadlines, exams, chapter progress, notices and cloud drive.
---

# 学习通连接器接入助手

把一个社区维护的只读 MCP 服务 `Xuexitong-mcp` 接进 WorkBuddy，让「查课表 / 查作业 DDL / 查考试 / 查进度 / 查通知 / 下资料」变成对话里的一条指令。

## 这个 Skill 解决什么

接入这件事本身不难，但有三处容易卡住，且官方文档不会同时讲清：

1. **凭据文件的落点**：服务端按「包目录的上一层 → 包目录」查找 `config.json`。用普通 `pip install .` 装到 site-packages 后，仓库里的 `config.json` 根本不会被读到；必须用可编辑安装 `pip install -e .` 或改用环境变量。
2. **连接器必须手动信任**：写进 `mcp.json` 只是登记，WorkBuddy 侧还要在「自定义连接器」里点一次「信任」，否则工具列表里永远看不到 `xuexitong`。
3. **命令要用绝对路径**：桌面客户端的 PATH 与终端不同，`"command": "python"` 经常直接拉不起来。

本 Skill 把这三处固定成脚本 + 检查清单，避免每次重新试错。

## 何时用 / 何时不用

**用**：

- 「帮我把学习通接到 WorkBuddy / 装个学习通 MCP」
- 「连接器里没有学习通，工具调不到」
- 「学习通登录失败 / cookie 失效 / 一直提示未登录」
- 「查一下我这周课表」「我有哪些作业快截止了」「导出课表到日历」

**不用**：

- 只要一份学习通作业的**内容创作**（写论文、做 PPT）——那是写作/Office 技能的事，本 Skill 只负责取数据。
- 签到、刷课、答题、批量爬取——服务端明确只读，不提供也不应绕过。
- 学校自有教务系统（非超星体系）——接口不通用。

## 前置条件与环境依赖

| 项 | 要求 | 说明 |
|---|---|---|
| 客户端 | WorkBuddy 桌面版 | 需要「连接器管理 → 自定义连接器」入口 |
| Python | 3.10 及以上 | 服务端 `requires-python >= 3.10` |
| 依赖包 | `mcp>=1.2.0`、`requests>=2.28`、`pycryptodome>=3.19` | `pip install -e .` 会自动装 |
| 服务端源码 | `https://github.com/DanMo661/Xuexitong-mcp` | 该包未发布到 PyPI，只能从源码安装 |
| 账号 | 本人学习通手机号 + 密码 | 仅支持账号密码登录，无扫码 |
| 网络 | 能访问 `*.chaoxing.com`、`*.cldisk.com` | 校园网/代理异常会表现为登录超时 |
| 权限 | 无需管理员权限 | 全部写入都在用户目录内 |

## 五步接入流程

### Step 1 安装服务端（可编辑安装）

```bash
git clone https://github.com/DanMo661/Xuexitong-mcp.git
cd Xuexitong-mcp
python -m pip install -e .
```

`-e` 不是可选项。可编辑安装让包目录仍指向仓库，`config.json` 与 `session_cookies.json` 才会落在你能看到、能改、能加进 `.gitignore` 的地方。

验证：`python -c "import xuexitong_mcp; print(xuexitong_mcp.__file__)"` 应输出**仓库内**的路径，而不是 site-packages。

### Step 2 配置凭据

三种来源，优先级从高到低：

1. 调用 `login` 工具时直接传 `phone` / `password`（最省事，但密码会进对话记录）
2. 环境变量 `CHAOXING_PHONE` / `CHAOXING_PASSWORD`（推荐，密码不落盘）
3. 仓库根目录 `config.json`（`config.example.json` 复制后填写）

移动端 passport 域名已下线，只能用网页版账号密码。

### Step 3 写入连接器配置

以下脚本都在**本 Skill 目录**下执行（`cd` 到 SKILL.md 所在目录）。

```bash
python scripts/register_mcp.py --python "C:/path/to/python.exe" --phone 13800000000
```

脚本做的事：备份现有 `mcp.json` → 只合并 `mcpServers.xuexitong` 一项 → 保留其他连接器不动 → 回显最终条目。常用开关：

```bash
python scripts/register_mcp.py --dry-run          # 只看将写入什么
python scripts/register_mcp.py --remove           # 卸载该连接器
python scripts/register_mcp.py --config "D:/tmp/mcp.json"   # 指定配置文件
```

`--python` 请传绝对路径；不传则用当前解释器。密码建议不加 `--password`，改用 `--phone` + 环境变量或 `config.json`。

### Step 4 在客户端信任连接器（人工，无法脚本化）

WorkBuddy 左下角 **+** 菜单 → **连接器管理** → 右上角 **自定义连接器** → 找到 `xuexitong` → 点 **信任**。

信任后需要新开一轮对话（或重连）才会加载工具。判断成功：工具列表出现 `mcp__xuexitong__*` 系列。

### Step 5 登录并验证

按顺序调用，任一步失败就转排错：

1. `login`（不传参数时自动读取环境变量或 `config.json`）
2. `get_profile` —— 应返回姓名、学校、学年学期
3. `get_schedule` —— 应返回本周课程

全链路体检（不改任何文件、不发网络请求）：

```bash
python scripts/check_env.py
```

输出逐项 `PASS / WARN / FAIL`：Python 版本、四个依赖、包安装位置、凭据来源、登录态文件、`mcp.json` 条目与命令可执行性、工具注册数量。

## 常用查询配方

| 需求 | 调用 | 备注 |
|---|---|---|
| 这周课表 | `get_schedule` 传 `week` | 不传 `week` 返回全学期汇总 |
| 导出日历 | `export_schedule_ics` 传 `save_dir` | 用学校真实节次时间，含课前 30 分钟提醒 |
| 作业 DDL 看板 | `get_homework_deadlines` | 逐课查详情，约 1 分钟，别放进循环 |
| 某课作业清单 | `list_homework` 传 `course` | `course` 是课名关键词，建议先 `list_courses` |
| 全课程进度 | `get_progress_overview` | 同样逐课扫描，较慢 |
| 找资料 | `find_materials` 传 `course` + `keyword` | 递归搜索，免逐层翻文件夹 |
| 未读通知 | `list_notices` 传 `unread_only` | 关键词过滤在本地做，范围约最近 100 条 |

## 输入输出约定

**输入**

- 凭据：手机号 + 密码，三选一来源（见 Step 2）。
- 课名：模糊关键词，精确同名优先，否则取第一个命中；课名有歧义时先 `list_courses` 拿全名。
- 路径：`save_dir` 必须是**已存在的绝对目录**；服务端只做文件名安全化，不创建目录。
- 范围：`horizon_days` 默认 90 天；`week` 为 1 基周次。

**输出**

- 所有查询类工具返回 **Markdown 纯文本**（人可读，非 JSON），直接在对话里引用即可。
- `download_material` / `export_schedule_ics` 会落盘，返回本地文件路径。
- 失败统一返回单行短消息，如「登录失败：密码错误」「未登录」——据此定位问题，不要重试超过一次。

## 校验标准

一次接入算成功，需同时满足：

1. `check_env.py` 无 `FAIL`。
2. `get_profile` 返回真实姓名与学校。
3. `get_schedule` 返回的课程与你本学期实际选课一致。
4. 重启客户端后工具仍在（证明配置持久化，不是内存态）。
5. 若要改动本仓库：`python -m unittest discover -s tests -v` 全绿。

## 排错路由

| 症状 | 先去这里 |
|---|---|
| 工具列表没有 `xuexitong` | Step 4 信任；`register_mcp.py --dry-run` 看条目 |
| 进程起不来 / 连接器红色 | 命令是否绝对路径；`--python` 指向的解释器能否 `import xuexitong_mcp` |
| 一直「未登录」 | `config.json` 是否在仓库根目录；是否用了非可编辑安装 |
| 「登录失败：密码错误」 | 密码近期是否改过；是否需要短信验证（风控） |
| 结果为空 / 课名找不到 | 先 `list_courses`，再传全名 |
| 请求超时 | 网络/代理；换网络重试一次，别连续重试 |

详细症状对照见 [references/troubleshooting.md](references/troubleshooting.md)。

## 安全边界

- **只读**：服务端全部为查询语义，不提交表单。不做签到、刷课、答题，不替代本人完成学习任务。
- **凭据不落库**：`config.json`、`session_cookies.json` 必须留在 `.gitignore` 里；写进 `mcp.json` 的密码等同于明文，优先用环境变量或 `config.json`。
- **风控**：学习通对高频请求敏感。不批量抓取、不做短间隔轮询；慢接口（DDL 看板、进度总览）一天几次即可。
- **仅限本人账号**：不要把他人账号接入，也不要多人共用一个会话文件。
- **接口非官方**：协议基于网页端逆向，学校或平台改版后可能失效，失效时升级服务端而非改脚本。

## 资源路由

| 文件 | 何时读 |
|---|---|
| `scripts/register_mcp.py` | 写入/更新/移除 `mcp.json` 条目 |
| `scripts/check_env.py` | 接入后体检、排错第一步 |
| `references/tools.md` | 查 16 个工具的参数、输出形态与耗时 |
| `references/troubleshooting.md` | 按症状查原因与修法 |
| `SECURITY.md` | 需要说明凭据落盘位置、信任边界或报告安全问题时 |
| `tests/test_skill.py` | 改动本仓库后跑 `python -m unittest discover -s tests -v` 自检 |
| `README.md` | 面向 GitHub 读者的安装说明 |
