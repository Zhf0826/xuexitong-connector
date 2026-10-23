#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一条命令完成学习通连接器配置。

做六件事：检查解释器 → 准备服务端源码 → 可编辑安装 → 写凭据 → 写 mcp.json → 自检。
唯一无法自动完成的是在 WorkBuddy 里点「信任」，脚本会把这一步作为最后提示打印出来。

常用：
    python scripts/setup.py                          # 交互式，一路到底
    python scripts/setup.py --phone 13800000000      # 密码用 getpass 交互输入
    python scripts/setup.py --credential-mode env    # 凭据写进 mcp.json 的 env
    python scripts/setup.py --dry-run                # 只打印计划，不落盘
    python scripts/setup.py --uninstall              # 移除连接器条目
"""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SERVER_REPO = "https://github.com/DanMo661/Xuexitong-mcp.git"
DEFAULT_SERVER = Path.home() / ".workbuddy" / "mcp-servers" / "xuexitong-mcp"
DEFAULT_MCP = Path.home() / ".workbuddy" / "mcp.json"

EXIT_OK = 0
EXIT_FAIL = 1


def log(step: str, msg: str = "") -> None:
    print(("[{}] {}".format(step, msg)).rstrip() if step else msg)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mask_phone(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 5) + value[-2:]


def check_python() -> None:
    v = sys.version_info
    if v < (3, 10):
        raise SystemExit(
            "Python {}.{} 低于要求，需要 3.10+。请换一个解释器重跑。".format(v.major, v.minor)
        )
    print("  解释器：{} ({}.{}.{})".format(sys.executable, v.major, v.minor, v.micro))


def importable() -> Path | None:
    """已安装则返回包目录。"""
    try:
        spec = importlib.util.find_spec("xuexitong_mcp")
    except Exception:
        return None
    if not spec or not spec.origin:
        return None
    return Path(spec.origin).resolve().parent


def ensure_source(server_dir: Path, allow_clone: bool, dry_run: bool) -> Path:
    if (server_dir / "xuexitong_mcp").is_dir():
        print("  服务端源码：{}（已存在）".format(server_dir))
        return server_dir

    pkg = importable()
    if pkg is not None:
        print("  服务端源码：{}（来自已安装包）".format(pkg.parent))
        return pkg.parent

    if not allow_clone:
        raise SystemExit(
            "未找到服务端源码：{}\n"
            "请先手动执行：\n"
            "  git clone {} \"{}\"\n"
            "然后重跑本脚本（或去掉 --no-clone 让脚本自动克隆）。".format(
                server_dir, SERVER_REPO, server_dir)
        )

    print("  服务端源码：未找到，准备克隆到 {}".format(server_dir))
    if dry_run:
        print("  [dry-run] 将执行：git clone {} {}".format(SERVER_REPO, server_dir))
        return server_dir

    server_dir.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", SERVER_REPO, str(server_dir)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            "克隆失败，请检查网络或 git 是否可用。\n"
            "  命令：git clone --depth 1 {} {}\n"
            "  错误：{}\n"
            "若公司/校园网限制，可手动下载源码后放到该目录再重跑。".format(
                SERVER_REPO, server_dir, (proc.stderr or proc.stdout).strip()[:400])
        )
    print("  服务端源码：克隆完成")
    return server_dir


def ensure_installed(server_dir: Path, dry_run: bool) -> None:
    pkg = importable()
    editable = pkg is not None and "site-packages" not in str(pkg).lower()
    if editable:
        print("  安装形态：可编辑安装，跳过 pip")
        return
    if pkg is not None and "site-packages" in str(pkg).lower():
        print("  安装形态：检测到普通安装（site-packages），将改为可编辑安装")

    cmd = [sys.executable, "-m", "pip", "install", "-e", str(server_dir), "--quiet"]
    print("  安装命令：python -m pip install -e {}".format(server_dir))
    if dry_run:
        print("  [dry-run] 跳过实际安装")
        return

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(
            "安装失败。请手动执行后重跑：\n"
            "  \"{}\" -m pip install -e \"{}\"\n"
            "  错误：{}".format(sys.executable, server_dir, (proc.stderr or proc.stdout).strip()[-400:])
        )
    print("  安装形态：可编辑安装完成")


def read_existing_config(server_dir: Path) -> dict:
    path = server_dir / "config.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_credentials(server_dir: Path, args) -> tuple[str, str]:
    existing = read_existing_config(server_dir)
    phone = args.phone or existing.get("phone") or ""
    password = existing.get("password") or ""

    if phone and password and not args.force_credentials:
        print("  凭据：复用现有 config.json（{}）".format(mask_phone(phone)))
        return phone, password

    if args.dry_run and not (phone and password):
        print("  [dry-run] 缺少凭据，按占位值继续演示流程")
        return "13800000000", "<dry-run>"

    if not phone:
        if args.yes:
            raise SystemExit("非交互模式必须提供 --phone，或在 config.json 里预置凭据。")
        phone = input("  学习通手机号：").strip()
    if not password:
        if args.yes:
            raise SystemExit("非交互模式请通过 config.json 预置密码，脚本不从参数读取明文密码。")
        password = getpass.getpass("  学习通密码（输入不回显）：")

    if not phone or not password:
        raise SystemExit("手机号或密码为空，已中止（未写入任何文件）。")
    return phone, password


def write_credentials(server_dir: Path, phone: str, password: str, mode: str, dry_run: bool) -> None:
    if mode == "env":
        print("  凭据载体：mcp.json 的 env（{}）".format(mask_phone(phone)))
        return
    path = server_dir / "config.json"
    print("  凭据载体：{}（{}）".format(path, mask_phone(phone)))
    if dry_run:
        print("  [dry-run] 跳过写入 config.json")
        return
    path.write_text(
        json.dumps({"phone": phone, "password": password}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if os.name == "posix":
        try:
            path.chmod(0o600)
        except OSError:
            pass
    print("  凭据载体：写入完成，已加入 .gitignore 覆盖范围（勿提交）")


def write_mcp_entry(phone: str, password: str, mode: str, config_path: Path, dry_run: bool) -> dict:
    reg = load_module("register_mcp", SKILL_ROOT / "scripts" / "register_mcp.py")
    data = reg.load_json(config_path)
    servers = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else {}
    existing = servers.get("xuexitong") if isinstance(servers.get("xuexitong"), dict) else {}

    env = dict(existing.get("env") or {}) if isinstance(existing.get("env"), dict) else {}
    env["CHAOXING_PHONE"] = phone
    if mode == "env":
        env["CHAOXING_PASSWORD"] = password
    else:
        env.pop("CHAOXING_PASSWORD", None)

    entry = reg.build_entry(str(Path(sys.executable)).replace("\\", "/"), env)
    servers["xuexitong"] = entry
    data["mcpServers"] = servers

    print("  配置目标：{}".format(config_path))
    print("  命令：{} -m xuexitong_mcp".format(entry["command"]))
    if dry_run:
        print("  [dry-run] 跳过写入 mcp.json")
        return entry

    backup = reg.backup(config_path)
    reg.write_json(config_path, data)
    if backup:
        reg.restrict_permissions(backup)
    verify = reg.load_json(config_path)
    if verify.get("mcpServers", {}).get("xuexitong") != entry:
        raise SystemExit("写入后回读校验失败，请检查 {}".format(config_path))
    print("  配置目标：写入成功{}".format("（已备份到 {}）".format(backup.name) if backup else ""))
    return entry


def run_selfcheck(config_path: Path, dry_run: bool) -> int:
    if dry_run:
        print("  [dry-run] 跳过自检")
        return EXIT_OK
    script = SKILL_ROOT / "scripts" / "check_env.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--config", str(config_path)],
        capture_output=True, text=True,
    )
    out = (proc.stdout or "").strip()
    tail = [line for line in out.splitlines() if line.startswith(("[PASS]", "[WARN]", "[FAIL]", "结果"))]
    for line in tail:
        print("  " + line)
    return EXIT_OK if proc.returncode == 0 else EXIT_FAIL


def uninstall(args) -> int:
    reg = load_module("register_mcp", SKILL_ROOT / "scripts" / "register_mcp.py")
    path = Path(args.config).expanduser().resolve()
    data = reg.load_json(path)
    servers = data.get("mcpServers") or {}
    if "xuexitong" not in servers:
        print("未找到 xuexitong 条目，无需移除。")
        return EXIT_OK
    servers.pop("xuexitong")
    data["mcpServers"] = servers
    backup = None if args.no_backup else reg.backup(path)
    reg.write_json(path, data)
    if backup:
        reg.restrict_permissions(backup)
    print("已移除连接器条目：{}".format(path))
    if args.purge:
        for name in ("config.json", "session_cookies.json"):
            for base in (Path(args.server_dir).expanduser(), DEFAULT_SERVER):
                target = base / name
                if target.exists():
                    target.unlink()
                    print("已删除凭据文件：{}".format(target))
    else:
        print("凭据文件保留（config.json / session_cookies.json）。需要一并清除请加 --purge。")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(
        description="一条命令完成学习通连接器配置",
        epilog="最后一步（在 WorkBuddy 里点信任）无法自动化，脚本会给出提示。",
    )
    parser.add_argument("--phone", default="", help="学习通手机号")
    parser.add_argument("--config", default=str(DEFAULT_MCP), help="mcp.json 路径")
    parser.add_argument("--server-dir", default=str(DEFAULT_SERVER), help="服务端源码目录")
    parser.add_argument("--credential-mode", choices=["config", "env"], default="config",
                        help="config=写入仓库 config.json；env=写入 mcp.json 的 env")
    parser.add_argument("--no-clone", action="store_true", help="不自动 git clone")
    parser.add_argument("--force-credentials", action="store_true", help="忽略已有凭据，重新输入")
    parser.add_argument("--with-shortcut", metavar="EXE", default="",
                        help="同时为本地学习通应用创建桌面快捷方式（Windows）")
    parser.add_argument("--yes", "-y", action="store_true", help="非交互模式")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写任何文件")
    parser.add_argument("--uninstall", action="store_true", help="移除连接器条目")
    parser.add_argument("--purge", action="store_true", help="卸载时一并删除凭据文件")
    parser.add_argument("--no-backup", action="store_true", help="卸载时不备份 mcp.json")
    args = parser.parse_args()

    if args.uninstall:
        return uninstall(args)

    server_dir = Path(args.server_dir).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()

    print("学习通连接器 · 一步安装")
    print("=" * 56)

    log("1/6", "检查 Python")
    check_python()

    log("2/6", "准备服务端源码")
    server_dir = ensure_source(server_dir, allow_clone=not args.no_clone, dry_run=args.dry_run)

    log("3/6", "安装服务端")
    ensure_installed(server_dir, args.dry_run)

    log("4/6", "配置凭据")
    phone, password = resolve_credentials(server_dir, args)
    write_credentials(server_dir, phone, password, args.credential_mode, args.dry_run)

    log("5/6", "写入连接器配置")
    write_mcp_entry(phone, password, args.credential_mode, config_path, args.dry_run)

    log("6/6", "自检")
    code = run_selfcheck(config_path, args.dry_run)

    if args.with_shortcut:
        print("可选：创建桌面入口")
        subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "make_shortcut.py"),
             "--target", args.with_shortcut],
            check=False,
        )

    print("=" * 56)
    if args.dry_run:
        print("dry-run 结束，未改动任何文件。")
        return EXIT_OK
    if code != EXIT_OK:
        print("自检未通过，请按上面 FAIL 项的提示处理后重跑本脚本。")
        return EXIT_FAIL

    print("配置已完成。最后一步（无法自动完成）：")
    print("  WorkBuddy 左下角 + → 连接器管理 → 右上角 自定义连接器 → 找到 xuexitong → 点「信任」")
    print("  然后新开一轮对话，说「查我的课表」即可验证。")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
