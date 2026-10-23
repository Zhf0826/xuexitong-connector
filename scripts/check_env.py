#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学习通连接器体检：只读检查，不修改文件、不发网络请求。

逐项输出 PASS / WARN / FAIL，并给出修复提示。退出码：0 全部通过或有告警，1 存在 FAIL。

示例：
    python check_env.py
    python check_env.py --json
    python check_env.py --no-tools --config D:/tmp/mcp.json
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import json
import os
import sys
from pathlib import Path

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
RESULTS: list[dict] = []


def add(status: str, item: str, detail: str, fix: str = "") -> None:
    RESULTS.append({"status": status, "item": item, "detail": detail, "fix": fix})


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 5) + value[-2:]


def pretty(path: str) -> str:
    try:
        home = str(Path.home())
        if home and str(path).lower().startswith(home.lower()):
            return "~" + str(path)[len(home):]
    except Exception:
        pass
    return str(path)


def check_python() -> None:
    v = sys.version_info
    ver = "{}.{}.{}".format(v.major, v.minor, v.micro)
    exe = pretty(sys.executable)
    if v >= (3, 10):
        add(PASS, "Python 版本", "{} ({})".format(ver, exe))
    else:
        add(FAIL, "Python 版本", "{} 低于 3.10".format(ver),
            "装 Python 3.10+ 后用它重新 pip install -e .")


def check_deps() -> None:
    for mod, label in (("mcp", "mcp"), ("requests", "requests"), ("Crypto", "pycryptodome")):
        try:
            importlib.import_module(mod)
            add(PASS, "依赖 " + label, "已安装")
        except Exception as exc:
            add(FAIL, "依赖 " + label, "导入失败：{}".format(exc),
                "python -m pip install -e . (在服务端仓库根目录执行)")


def check_package() -> Path | None:
    try:
        pkg = importlib.import_module("xuexitong_mcp")
    except Exception as exc:
        add(FAIL, "服务端包", "无法导入 xuexitong_mcp：{}".format(exc),
            "git clone 仓库后执行 python -m pip install -e .")
        return None

    pkg_file = Path(getattr(pkg, "__file__", "") or "").resolve()
    pkg_dir = pkg_file.parent
    try:
        version = md.version("Xuexitong-mcp")
    except Exception:
        version = getattr(pkg, "__version__", "unknown")

    editable = "site-packages" not in str(pkg_dir).lower()
    detail = "{}  版本 {}  位置 {}".format(
        "可编辑安装" if editable else "普通安装", version, pretty(str(pkg_file)))
    if editable:
        add(PASS, "服务端包", detail)
    else:
        add(WARN, "服务端包", detail,
            "普通安装会导致仓库根目录的 config.json 读不到；建议 pip install -e . 或改用环境变量")
    return pkg_dir


def find_config(pkg_dir: Path | None) -> Path | None:
    if pkg_dir is None:
        return None
    for candidate in (pkg_dir.parent / "config.json", pkg_dir / "config.json"):
        if candidate.exists():
            return candidate
    return None


def check_credentials(pkg_dir: Path | None) -> None:
    env_phone = os.environ.get("CHAOXING_PHONE", "")
    env_pwd = os.environ.get("CHAOXING_PASSWORD", "")
    cfg = find_config(pkg_dir)

    sources = []
    if env_phone:
        sources.append("环境变量 CHAOXING_PHONE=" + mask(env_phone))
    if env_pwd:
        sources.append("环境变量 CHAOXING_PASSWORD=" + mask(env_pwd))
    if env_phone and not env_pwd:
        add(WARN, "凭据", "有 CHAOXING_PHONE 但缺少 CHAOXING_PASSWORD",
            "补齐密码环境变量，或改用 config.json")

    cfg_ok = False
    if cfg is not None:
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            if data.get("phone") and data.get("password"):
                cfg_ok = True
                sources.append("config.json " + pretty(str(cfg)))
            else:
                add(WARN, "凭据", "config.json 缺少 phone 或 password 字段",
                    "键名必须是 phone 与 password")
        except Exception as exc:
            add(WARN, "凭据", "config.json 无法解析：{}".format(exc),
                "对照 config.example.json 重写，UTF-8 编码")

    if sources:
        add(PASS, "凭据", "；".join(sources))
    elif cfg is None:
        add(FAIL, "凭据", "环境变量与 config.json 都没有",
            "在仓库根目录放 config.json（phone/password），或在 mcp.json 的 env 里配 "
            "CHAOXING_PHONE/CHAOXING_PASSWORD")
    elif not cfg_ok:
        add(FAIL, "凭据", "config.json 存在但不可用", "对照 config.example.json 重写该文件")


def check_session(pkg_dir: Path | None) -> None:
    if pkg_dir is None:
        return
    for candidate in (pkg_dir.parent / "session_cookies.json", pkg_dir / "session_cookies.json"):
        if candidate.exists():
            size = candidate.stat().st_size
            add(PASS, "登录态文件", "{} ({} 字节)".format(pretty(str(candidate)), size))
            return
    add(WARN, "登录态文件", "尚未生成",
        "首次调用 login 工具后才会出现，属正常；若已登录仍无此文件，检查目录是否可写")


def check_mcp_entry(config_path: Path) -> None:
    if not config_path.exists():
        add(FAIL, "连接器配置", "未找到 {}".format(pretty(str(config_path))),
            "python scripts/register_mcp.py --python <解释器绝对路径>")
        return
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        add(FAIL, "连接器配置", "mcp.json 解析失败：{}".format(exc), "修复 JSON 语法后重试")
        return

    entry = (data.get("mcpServers") or {}).get("xuexitong")
    if not isinstance(entry, dict):
        add(FAIL, "连接器配置", "mcp.json 里没有 xuexitong 条目",
            "python scripts/register_mcp.py --python <解释器绝对路径>")
        return

    command = str(entry.get("command", ""))
    args = entry.get("args") or []
    problems = []
    if not command:
        problems.append("缺少 command")
    elif not Path(command).exists():
        problems.append("command 指向的文件不存在：{}".format(pretty(command)))
    if list(args) != ["-m", "xuexitong_mcp"]:
        problems.append("args 应为 -m xuexitong_mcp，实际 {}".format(args))

    env = entry.get("env") or {}
    if env:
        keys = ", ".join(sorted(env))
        add(WARN, "连接器 env", "含明文凭据键：{}".format(keys),
            "如不希望密码落盘，改用仓库根目录的 config.json")

    if problems:
        add(FAIL, "连接器配置", "；".join(problems),
            "python scripts/register_mcp.py --python <解释器绝对路径> 重新写入")
    else:
        add(PASS, "连接器配置", "条目完整：{} -m xuexitong_mcp".format(pretty(command)))


def check_tools() -> None:
    try:
        server = importlib.import_module("xuexitong_mcp.server")
        mcp = getattr(server, "mcp")
        import asyncio

        tools = asyncio.run(mcp.list_tools())
        names = sorted(getattr(t, "name", str(t)) for t in tools)
        count = len(names)
        detail = "{} 个工具：{}".format(count, ", ".join(names))
        if count >= 16:
            add(PASS, "工具注册", detail)
        else:
            add(WARN, "工具注册", detail, "服务端版本可能较旧，升级到最新版再试")
    except Exception as exc:
        add(WARN, "工具注册", "无法枚举工具：{}".format(exc),
            "确认 mcp 版本 >= 1.2.0；不影响连接器本身启动")


def main() -> int:
    parser = argparse.ArgumentParser(description="学习通连接器环境体检（只读）")
    parser.add_argument("--config", default=str(Path.home() / ".workbuddy" / "mcp.json"),
                        help="mcp.json 路径（默认 ~/.workbuddy/mcp.json）")
    parser.add_argument("--no-tools", action="store_true", help="跳过工具枚举")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，便于脚本消费")
    args = parser.parse_args()

    check_python()
    check_deps()
    pkg_dir = check_package()
    check_credentials(pkg_dir)
    check_session(pkg_dir)
    check_mcp_entry(Path(args.config).expanduser().resolve())
    if not args.no_tools:
        check_tools()

    fails = sum(1 for r in RESULTS if r["status"] == FAIL)
    warns = sum(1 for r in RESULTS if r["status"] == WARN)

    if args.json:
        print(json.dumps({"results": RESULTS, "fail": fails, "warn": warns},
                         ensure_ascii=False, indent=2))
    else:
        print("学习通连接器体检")
        print("=" * 56)
        for r in RESULTS:
            print("[{}] {:<10} {}".format(r["status"], r["item"], r["detail"]))
            if r["fix"] and r["status"] != PASS:
                print("       -> {}".format(r["fix"]))
        print("=" * 56)
        print("结果：{} 项通过，{} 项告警，{} 项失败".format(
            len(RESULTS) - fails - warns, warns, fails))
        if fails:
            print("先解决 FAIL 项，再回到 SKILL.md 的 Step 4 检查连接器是否已信任。")

    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
