#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Xuexitong-mcp 注册为 WorkBuddy 自定义连接器（幂等、可回滚）。

只改 mcpServers 下的单个条目，其余连接器原样保留；写入前自动备份。

示例：
    python register_mcp.py --python C:/Python312/python.exe --phone 13800000000
    python register_mcp.py --dry-run
    python register_mcp.py --remove
    python register_mcp.py --config D:/tmp/mcp.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

SERVER_KEY = "xuexitong"
MODULE_ARGS = ["-m", "xuexitong_mcp"]


def default_config_path() -> Path:
    """WorkBuddy 桌面版的用户级 MCP 配置位置。"""
    return Path.home() / ".workbuddy" / "mcp.json"


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 5) + value[-2:]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "配置文件不是合法 JSON，已中止（未做任何修改）：\n  {}\n  错误：{}".format(path, exc)
        )
    if not isinstance(data, dict):
        raise SystemExit("配置文件顶层必须是 JSON 对象，已中止：{}".format(path))
    return data


def build_entry(python_exe: str, env: dict) -> dict:
    return {
        "type": "stdio",
        "command": python_exe,
        "args": list(MODULE_ARGS),
        "env": env,
    }


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(path.name + ".bak-" + stamp)
    shutil.copy2(path, target)
    return target


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    restrict_permissions(path)


def restrict_permissions(path: Path) -> None:
    """mcp.json 可能含明文凭据，POSIX 下收紧到仅本人可读写。"""
    if os.name != "posix":
        return
    try:
        path.chmod(0o600)
    except OSError:
        pass


def describe(entry: dict) -> str:
    env = entry.get("env") or {}
    safe_env = {k: mask(str(v)) for k, v in env.items()}
    lines = [
        "  type   : " + str(entry.get("type")),
        "  command: " + str(entry.get("command")),
        "  args   : " + " ".join(str(a) for a in entry.get("args") or []),
        "  env    : " + (json.dumps(safe_env, ensure_ascii=False) if safe_env else "{}"),
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="注册/更新/移除 WorkBuddy 的 xuexitong 自定义 MCP 连接器",
        epilog="安全提示：--password 会把口令写进 shell 历史与 mcp.json。"
               "优先用环境变量或仓库根目录的 config.json，并确保该目录权限为仅本人可读。",
    )
    parser.add_argument("--config", default=str(default_config_path()),
                        help="mcp.json 路径（默认 ~/.workbuddy/mcp.json）")
    parser.add_argument("--name", default=SERVER_KEY, help="连接器键名（默认 xuexitong）")
    parser.add_argument("--python", default=sys.executable,
                        help="运行 MCP 服务的 Python 解释器绝对路径（默认当前解释器）")
    parser.add_argument("--phone", default="", help="写入 env 的 CHAOXING_PHONE")
    parser.add_argument("--password", default="", help="写入 env 的 CHAOXING_PASSWORD（不推荐）")
    parser.add_argument("--no-backup", action="store_true", help="跳过备份")
    parser.add_argument("--dry-run", action="store_true", help="只打印将写入的内容")
    parser.add_argument("--remove", action="store_true", help="移除该连接器条目")
    args = parser.parse_args()

    path = Path(args.config).expanduser().resolve()
    data = load_json(path)
    servers = data.get("mcpServers")
    if servers is None:
        servers = {}
    if not isinstance(servers, dict):
        raise SystemExit("mcpServers 不是对象，已中止：{}".format(path))

    existing = servers.get(args.name)

    if args.remove:
        if existing is None:
            print("未找到 {} 条目，无需移除：{}".format(args.name, path))
            return 0
        servers.pop(args.name)
        data["mcpServers"] = servers
        if args.dry_run:
            print("[dry-run] 将从 {} 移除条目：{}".format(path, args.name))
            return 0
        bk = None if args.no_backup else backup(path)
        write_json(path, data)
        if bk:
            restrict_permissions(bk)
        print("已移除 {}：{}".format(args.name, path))
        if bk:
            print("备份：{}".format(bk))
        print("提示：下一步到 连接器管理 - 自定义连接器 里确认该条目消失，必要时重启客户端。")
        return 0

    python_exe = str(Path(args.python).expanduser()).replace("\\", "/")

    env = {}
    if isinstance(existing, dict) and isinstance(existing.get("env"), dict):
        env.update({str(k): str(v) for k, v in existing["env"].items()})
    if args.phone:
        env["CHAOXING_PHONE"] = args.phone
    if args.password:
        env["CHAOXING_PASSWORD"] = args.password

    entry = build_entry(python_exe, env)

    if existing == entry:
        print("条目已是最新，无需改动：{}".format(path))
        print(describe(entry))
        return 0

    servers[args.name] = entry
    data["mcpServers"] = servers

    print("目标配置：{}".format(path))
    print("动作：{}".format("更新已有条目" if existing is not None else "新增条目"))
    print(describe(entry))

    if not Path(python_exe).exists():
        print("警告：command 指向的解释器不存在，连接器会启动失败。")

    if args.dry_run:
        print("[dry-run] 未写入任何文件。")
        return 0

    bk = None if args.no_backup else backup(path)
    write_json(path, data)
    if bk:
        restrict_permissions(bk)

    # 回读校验，避免写出坏文件
    verify = load_json(path)
    ok = verify.get("mcpServers", {}).get(args.name) == entry
    print("写入{}".format("成功" if ok else "后校验失败，请检查文件"))
    if bk:
        print("备份：{}".format(bk))
    if not ok:
        return 1

    if env:
        print("注意：env 中保存了明文凭据，键为 {}。如不希望落盘，改用仓库根目录的 config.json。".format(
            ", ".join(sorted(env))))
    print("下一步：连接器管理 - 右上角自定义连接器 - 找到 {} - 点击信任，然后新开一轮对话。".format(
        args.name))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
