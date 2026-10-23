# 常见问题

## 一、安装与信任

**Q1 为什么最后一步「信任」不能自动完成？**

连接器是绑定在你本机客户端上的授权动作，设计上就必须由人确认——否则任何脚本都能悄悄把你的账号接进某个程序。脚本能做的都做了（装好、配好、自检通过），只剩这一下点击。

**Q2 我点完信任，工具还是没出现？**

当前会话不会热加载。新开一轮对话，或重启客户端。判断标准：工具列表出现 `mcp__xuexitong__*`。

**Q3 为什么一定要 `pip install -e .`，`pip install .` 不行吗？**

服务端按「包目录 → 包目录上一层」查找 `config.json`。普通安装会把包放进 `site-packages`，仓库里的 `config.json` 根本不会被读到，表现为怎么登录都提示「未登录」。`-e` 让包目录仍指向仓库，凭据文件才在你能看到、能改、能加进 `.gitignore` 的地方。

**Q4 一键脚本能重复跑吗？**

能。每一步都是幂等的：源码在就跳过克隆，已是可编辑安装就跳过 pip，凭据在就复用，`mcp.json` 只有条目变化才写，写前自动备份。想强制重新输入凭据加 `--force-credentials`。

**Q5 我换电脑了，怎么迁移？**

新电脑上重跑一次 `python scripts/setup.py` 就行。**不要**复制 `session_cookies.json`——换机器后会话基本立即失效，还可能触发风控。`config.json` 可以复制，但更推荐重新输入。

## 二、凭据与安全

**Q6 我的密码存在哪里？**

看你选的模式：

- `--credential-mode config`（默认）：仓库根目录的 `config.json`，POSIX 下权限 `0600`
- `--credential-mode env`：`~/.workbuddy/mcp.json` 里的 `env` 字段（明文，集中在一个文件）

两种都在用户目录内，都不会进 git（`.gitignore` 已排除，CI 也会复查）。脚本不接受命令行明文密码，日志里手机号一律掩码。

**Q7 会不会被封号？**

它只做查询，频率完全由你用对话的节奏决定，不做批量抓取、不做短间隔轮询，正常备课使用与在网页上点几下没有区别。风险来自滥用：拿它爬全站资料、定时一分钟轮询一次 DDL——这种事别做。

**Q8 别人能用我的配置吗？**

不能，也不应该。`config.json` 是你的账号凭据，`session_cookies.json` 等价于登录态。发给别人等于把账号借出去。

## 三、使用

**Q9 查作业 DDL 为什么这么慢？**

截止时间只存在于每份作业的详情页，所以 `get_homework_deadlines` 必须逐份请求，全课程约一分钟。缩小范围：传 `course` 限定单课，或调小 `horizon_days`。别放进循环。

**Q10 课表怎么只有当前周？**

学习通接口的默认行为：不带参数只返回当前周。要全学期就让 `get_schedule` 不传 `week`（客户端逐周合并，约十秒）；要某一周就显式传 `week`。

**Q11 为什么课名匹配错了？**

`course` 是子串匹配，精确同名优先，否则取第一个命中。先 `list_courses` 拿完整课名再传。

**Q12 支持 macOS / Linux 吗？**

MCP 链路三平台通用。`make_shortcut.py`（桌面快捷方式）只支持 Windows，非 Windows 会直接退出并说明原因。

## 四、故障

**Q13 校园网下克隆或登录超时怎么办？**

先换网络（手机热点）验证是否是出口限制。克隆失败可以手动下载源码放到 `--server-dir`，再加 `--no-clone` 重跑。登录超时不要连续重试，间隔几分钟。

**Q14 提示「凭据存在但不可用」？**

`config.json` 字段名必须是 `phone` 与 `password`，不是 `username` / `pwd`；文件用 UTF-8。改完重跑脚本即可。

**Q15 卸载干净要几步？**

```bash
python scripts/setup.py --uninstall --purge   # 移除条目并删凭据文件
python -m pip uninstall Xuexitong-mcp         # 卸载包
```

`--uninstall` 默认保留凭据文件（下次重装不用再输密码），加 `--purge` 才删。

**Q16 服务端升级了怎么跟？**

```bash
cd ~/.workbuddy/mcp-servers/xuexitong-mcp && git pull
```

更新后不需要改 `mcp.json`，重启客户端即可。
