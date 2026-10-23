# xuexitong-connector

[![CI](https://github.com/Zhf0826/xuexitong-connector/actions/workflows/ci.yml/badge.svg)](https://github.com/Zhf0826/xuexitong-connector/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-informational.svg)](CHANGELOG.md)

把**超星学习通**接进 WorkBuddy 的 Skill：安装只读 MCP 服务 → 注册为自定义连接器 → 信任启用 → 登录验证，然后用一句话查课表、作业 DDL、考试、章节进度、通知和资料。

安装后可**一条命令**跑完前面五步中的四步，你只需要在客户端点一次「信任」。

不是又一个「学习通自动化脚本」。这里只有**查询**：不签到、不刷课、不答题、不代做作业。

## 为什么需要它

`Xuexitong-mcp` 本身已经把接口跑通了，但接入 WorkBuddy 的过程中有三处反复踩坑，且现有文档不会同时讲清：

| 坑 | 现象 | 本 Skill 的处理 |
|---|---|---|
| 凭据文件落点 | `pip install .` 装到 site-packages 后，仓库里的 `config.json` 永远读不到，一直提示未登录 | 强制可编辑安装 `pip install -e .`，并在体检脚本里识别安装形态 |
| 连接器需手动信任 | 写进 `mcp.json` 后工具列表依然空白 | 把「信任」写成显式步骤，并给出验证判据 |
| 命令用裸 `python` | 连接器启动失败，桌面进程 PATH 与终端不同 | 注册脚本要求解释器绝对路径，写入后回读校验 |

## 前置条件

- WorkBuddy 桌面版（需要「连接器管理 → 自定义连接器」入口）
- Python 3.10+
- 学习通账号（手机号 + 密码，仅网页端账号体系）
- 能访问 `*.chaoxing.com`、`*.cldisk.com`

## 安装

### 一条命令（推荐）

```bash
git clone https://github.com/Zhf0826/xuexitong-connector.git
cd xuexitong-connector
python scripts/setup.py
```

脚本会依次完成：检查 Python → 克隆/定位服务端 → 可编辑安装 → 询问手机号与密码 → 写入 `mcp.json` → 9 项体检。跑完只剩一步：

> WorkBuddy 左下角 **+** → **连接器管理** → 右上角 **自定义连接器** → 找到 `xuexitong` → **信任**

信任后新开一轮对话，说「查我的课表」即可验证。

常用变体：

| 场景 | 命令 |
|---|---|
| 已手动放好源码 | `python scripts/setup.py --no-clone` |
| 想先看会改什么 | `python scripts/setup.py --dry-run` |
| 密码不想落盘到 `config.json` | `python scripts/setup.py --credential-mode env` |
| 顺手建桌面快捷方式 | `python scripts/setup.py --with-shortcut "D:/学习/cxstudy/cxstudy.exe"` |
| 卸载 | `python scripts/setup.py --uninstall --purge` |

### 手动模式（脚本失败时的兜底）

<details>
<summary>点开看五个步骤</summary>

**1. 装服务端（可编辑安装）**

```bash
git clone https://github.com/DanMo661/Xuexitong-mcp.git
cd Xuexitong-mcp
python -m pip install -e .
```

验证包指向仓库而不是 site-packages：

```bash
python -c "import xuexitong_mcp; print(xuexitong_mcp.__file__)"
```

**2. 配凭据**

优先级：`login` 工具参数 > 环境变量 > `config.json`

```bash
cp config.example.json config.json   # Windows: copy
```

```json
{
  "phone": "13800000000",
  "password": "your-password"
}
```

**3. 注册连接器**

```bash
python scripts/register_mcp.py --python "C:/Python312/python.exe" --phone 13800000000
```

**4. 信任并启用**

WorkBuddy 左下角 **+** → **连接器管理** → 右上角 **自定义连接器** → `xuexitong` → **信任**。

**5. 体检**

```bash
python scripts/check_env.py
```

</details>

## 用法示例

| 你说 | 实际调用 |
|---|---|
| 这周还有什么课 | `get_schedule` 传本周 `week` |
| 我有哪些作业快截止了 | `get_homework_deadlines` |
| 「数字电路」还有几次作业没交 | `list_courses` → `list_homework` |
| 把这学期课表导出到日历 | `export_schedule_ics` |
| 资料区有没有往年的真题 | `find_materials` 传 `keyword` |

16 个工具的参数、耗时与输出形态见 [references/tools.md](references/tools.md)。

## 目录结构

```text
xuexitong-connector/
├── SKILL.md                    # 技能主入口：五步接入流程与边界
├── README.md                   # 本文件（GitHub 首页）
├── SECURITY.md                 # 信任边界、凭据落盘与风险分级
├── CHANGELOG.md                # 版本记录
├── LICENSE                     # MIT
├── .gitignore                  # 排除凭据、登录态与打包产物
├── .github/workflows/ci.yml    # Python 3.11 / 3.13 双版本自检
├── agents/
│   └── openai.yaml             # UI 展示元数据
├── evals/
│   └── evals.json              # 触发/不触发用例
├── references/
│   ├── tools.md                # 16 个工具的参数与输出
│   ├── troubleshooting.md      # 按症状排错
│   └── faq.md                  # 安装、凭据、使用、故障四类问答
├── scripts/
│   ├── setup.py                # 一条命令接入：装、配、写、检
│   ├── register_mcp.py         # 只重写/移除 mcp.json 条目
│   ├── check_env.py            # 只读体检：依赖、安装形态、凭据、条目、工具数
│   └── make_shortcut.py        # Windows 快捷方式：三级回退 + 回读校验
└── tests/
    └── test_skill.py           # 23 项仓库自检（零第三方依赖）
```

## 测试

```bash
python -m unittest discover -s tests -v
```

23 项检查，全部离线：frontmatter 与目录名一致性、SKILL 与 README 本地链接是否失效、四个脚本的语法与 `--help` 契约、`build_entry` 与掩码逻辑、一键安装是否提示人工信任步骤、快捷方式三级回退是否齐全、凭据文件是否混入仓库、疑似密钥与私人路径扫描、打包元数据完整性。CI 在 Python 3.11 与 3.13 上各跑一遍。

## 安全说明

- **只读**：服务端全部为查询语义，不提交表单。
- **凭据**：`config.json` 与 `session_cookies.json` 已在 `.gitignore` 中排除，自检会在 CI 里复查。写进 `mcp.json` 的 env 是明文，POSIX 下注册脚本会把该文件权限收紧到 `0600`；介意就用 `config.json`。
- **风控**：学习通对高频请求敏感。不要批量抓取、不要短间隔轮询；`get_homework_deadlines` 与 `get_progress_overview` 会逐课扫描，一次约一分钟。
- **仅限本人账号**：请勿接入他人账号。

完整边界与报告方式见 [SECURITY.md](SECURITY.md)。安装、凭据、使用、故障四类问答见 [references/faq.md](references/faq.md)。

## 已知限制

成绩单页对程序化访问返回 403；学号接口已停用；站内消息、讨论区、错题集、云盘下载均不支持。详见 [references/tools.md](references/tools.md) 末节。

## 致谢与许可

服务端由 [Wu Jiale](https://github.com/DanMo661) 开发，MIT 许可，仓库：[DanMo661/Xuexitong-mcp](https://github.com/DanMo661/Xuexitong-mcp)。

本 Skill 仅封装接入流程与排错经验，同样以 MIT 发布。协议基于网页端逆向，学校或平台改版后可能失效——失效时升级服务端版本，而不是改这里的脚本。

本项目与超星学习通官方无关。
