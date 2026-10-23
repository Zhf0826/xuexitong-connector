# 排错对照表

按症状从上往下排查。每步先看**证据**，再动手改配置。

## 一、连接器层

### 连接器列表里看不到 `xuexitong`

1. `python scripts/register_mcp.py --dry-run` 确认条目已写入 `mcp.json`。
2. 确认配置文件位置正确：桌面版读的是 `~/.workbuddy/mcp.json`（**不是** `.mcp.json`）。
3. 到「连接器管理 → 自定义连接器」点「信任」。只写文件不点信任，等于没接。
4. 信任后新开一轮对话；当前会话不会热加载。

### 连接器显示红色 / 启动失败

| 检查 | 命令 | 期望 |
|---|---|---|
| 命令是绝对路径 | 打开 `mcp.json` 看 `command` | 形如 `C:/Python312/python.exe`，不是 `python` |
| 解释器能导入包 | `"<该解释器>" -c "import xuexitong_mcp; print(xuexitong_mcp.__file__)"` | 打印仓库内路径 |
| 依赖齐全 | `python scripts/check_env.py` | 四个依赖全 PASS |
| 入口可用 | `"<该解释器>" -m xuexitong_mcp` | 不报 `ModuleNotFoundError`；stdio 模式会静默等待输入，Ctrl+C 退出 |

常见根因：装到了 A 解释器，配置里写的是 B 解释器；或用了裸 `python`，桌面进程继承的 PATH 里没有目标解释器。

## 二、登录层

### 「未登录」反复出现

先分清是「凭据没读到」还是「读到了但失效」：

- 跑 `python scripts/check_env.py`，看 `凭据来源` 一项。
- 若显示 `none`：说明三处都没有。注意 `config.json` 必须在**仓库根目录**（与 `config.example.json` 同级），不是当前工作目录。
- 若显示 `config.json` 但登录失败：文件里键名是 `phone` / `password`，不是 `username` / `pwd`。
- 若用的是非可编辑安装（`pip install .` 而非 `-e .`），包目录在 site-packages，仓库里的 `config.json` 不会被读到——改回可编辑安装，或改用环境变量。

### 「登录失败：密码错误」

- 密码是否近期修改；先用浏览器登录一次确认。
- 账号是否需要短信/图形验证：频繁登录会触发风控，客户端无法过验证码，等 10–30 分钟再试或先手动登录一次解除。
- 手机号是否为登录手机号（不是学号）。

### 登录成功但立刻又失效

- `session_cookies.json` 目录是否可写；只读目录会导致会话存不下来。
- 是否有多个进程共用同一份 cookie 文件（桌面悬浮窗 + MCP 同时跑）；串行使用，别并发登录。
- 学校门户做了单点登录互踢。

## 三、数据层

### 查不到课程 / `course` 匹配错误

`course` 是子串匹配，顺序取第一个命中。先 `list_courses` 拿完整课名再传。

### 课表只有当前周

这是接口行为：不传 `week` 时只返回当前周。要全学期汇总，让客户端逐周合并（`get_schedule` 不传参即走这条路，约 10 秒）。要某一周就显式传 `week`。

### 截止时间显示「截止未知」

详情页本身没有截止信息（常见于报告类作业），不是解析 bug。

### DDL 看板很慢 / 超时

`get_homework_deadlines` 对每份未交作业单独请求详情，全课程约 1 分钟。缩小范围：传 `course` 限定单课，或调小 `horizon_days`。不要放在循环或定时任务里高频跑。

### 下载 403

下载链接必须带 `Referer: https://pan-yz.chaoxing.com/`，客户端已处理；仍 403 多为链接过期，重新 `list_materials` 拿新的 `data_id` 再下。

### 中文文件名乱码

CDN 的 `filename*` 是非标裸 UTF-8，需 latin-1→utf-8 修复，客户端已处理；自行改脚本时注意别二次解码。

## 四、网络与平台层

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 请求超时 | 校园网代理、DNS 污染、出口限制 | 换网络重试一次，不要连续重试 |
| 429 / 502 / 503 / 504 | 服务端限流或维护 | 客户端已带指数退避；仍失败就等待，别压测 |
| 成绩页 403 | WAF 拒绝程序化访问 | 无解，改用作业得分 + 考试分数 |
| 全部工具突然失效 | 学校或平台改版 | 升级服务端版本，而不是改本 Skill 的脚本 |

## 五、回收与重装

```bash
python scripts/register_mcp.py --remove     # 摘掉连接器条目，保留其他连接器
python -m pip uninstall Xuexitong-mcp       # 卸载包
```

凭据与登录态需要手工删：仓库根目录的 `config.json`、`session_cookies.json`。卸载包不会删它们。

## 六、给维护者的最小复现信息

报 issue 时附上：

1. `python -c "import sys; print(sys.version)"`
2. `python -c "import xuexitong_mcp; print(xuexitong_mcp.__file__)"`
3. `check_env.py` 的输出（**确认无密码**）
4. `mcp.json` 里 `xuexitong` 那一段（**删掉 env 中的密码**）
5. 具体工具名 + 返回的单行错误文案
