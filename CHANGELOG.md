# 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## [1.1.0] - 2026-10-23

### Added

- `tests/test_skill.py`：17 项仓库自检，覆盖 frontmatter、本地链接、脚本契约、凭据文件与密钥扫描、打包元数据。零第三方依赖，`python -m unittest discover -s tests` 即可跑。
- `.github/workflows/ci.yml`：push 与 PR 在 Python 3.11 / 3.13 双版本跑自检与语法编译。
- `SECURITY.md`：信任边界、凭据落盘位置与风险分级、自动化行为说明、问题报告方式。
- `CHANGELOG.md`：本文件。
- README 增加 CI 徽章、测试说明与安全说明入口。

### Changed

- `scripts/register_mcp.py`：写入 `mcp.json` 及其备份后，在 POSIX 下将权限收紧到 `0600`；`--password` 的帮助文本补充「会进 shell 历史」的提示。
- `SKILL.md` 版本升至 1.1.0，资源路由补 `SECURITY.md` 与 `tests/`。

### Security

- 自检会拒绝 `config.json`、`session_cookies.json`、`.env` 出现在仓库内，并对疑似密钥与私人用户目录路径做正则扫描。

## [1.0.0] - 2026-10-23

### Added

- `SKILL.md`：五步接入流程（可编辑安装 → 凭据 → 注册连接器 → 信任启用 → 登录验证），含校验标准、输入输出约定与安全边界。
- `scripts/register_mcp.py`：幂等写入 `mcp.json`，自动备份、只合并单项、回读校验，支持 `--dry-run` 与 `--remove`。
- `scripts/check_env.py`：只读体检，9 项 PASS/WARN/FAIL，识别安装形态与工具注册数量。
- `references/tools.md`：16 个工具的参数、耗时与输出形态；`references/troubleshooting.md`：按症状排错。
- `evals/evals.json`、`agents/openai.yaml`、`LICENSE`（MIT）、`.gitignore`。
