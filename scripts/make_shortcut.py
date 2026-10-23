#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为本地应用创建 Windows 快捷方式（.lnk），并回读校验。

对应教学视频里的「桌面学习通连接器」：把快捷方式指向真实 exe、写对工作目录，
再读回目标确认可解析——而不是只写一个看起来对的图标。

三级回退，任一条成功即可：
  1. ctypes 直连 COM（IShellLinkW + IPersistFile），不依赖任何第三方包
  2. pywin32 的 win32com.client
  3. PowerShell 的 WScript.Shell

示例：
    python scripts/make_shortcut.py --target "D:/学习/cxstudy/cxstudy.exe"
    python scripts/make_shortcut.py --target app.exe --name 学习通 --link "D:/demo/学习通.lnk"
    python scripts/make_shortcut.py --target app.exe --verify-only --link "D:/demo/学习通.lnk"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path


# ---------------------------------------------------------------- 路径与校验

def default_link(name: str) -> Path:
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    if not desktop.is_dir():
        desktop = Path.home()
    return desktop / (name + ".lnk")


def verify_lnk(link: Path) -> str | None:
    """读回 .lnk 的目标路径；失败返回 None。"""
    if not link.exists():
        return None

    if sys.platform == "win32":
        try:
            target = _com_read(link)
            if target:
                return target
        except Exception:
            pass
        try:
            return _powershell_read(link)
        except Exception:
            pass
    return None


# ---------------------------------------------------------------- COM（ctypes）

def _guid(text: str):
    import ctypes
    from ctypes import wintypes

    u = uuid.UUID(text)
    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]
    g = GUID()
    g.Data1 = u.time_low
    g.Data2 = u.time_mid
    g.Data3 = u.time_hi_version
    for i, b in enumerate(u.bytes[8:]):
        g.Data4[i] = b
    return g


def _com_create():
    import ctypes
    from ctypes import wintypes

    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)

    clsid = _guid("00021401-0000-0000-C000-000000000046")   # ShellLink
    iid = _guid("000214F9-0000-0000-C000-000000000046")     # IShellLinkW
    ptr = ctypes.c_void_p()
    hr = ole32.CoCreateInstance(
        ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(ptr)
    )
    if hr != 0 or not ptr:
        raise RuntimeError("CoCreateInstance 失败，HRESULT=0x{:08X}".format(hr & 0xFFFFFFFF))
    return ptr


def _vtbl_call(ptr, index: int, restype, argtypes, *args):
    import ctypes

    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    func = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])
    return func(ptr, *args)


def _com_write(link: Path, target: Path, workdir: Path) -> None:
    import ctypes

    ptr = _com_create()
    try:
        # IShellLinkW 虚表：9 = SetWorkingDirectory, 20 = SetPath
        _vtbl_call(ptr, 20, ctypes.c_long, [ctypes.c_wchar_p], str(target))
        _vtbl_call(ptr, 9, ctypes.c_long, [ctypes.c_wchar_p], str(workdir))

        pf = ctypes.c_void_p()
        _query_interface(ptr, "0000010b-0000-0000-C000-000000000046", ctypes.byref(pf))
        _vtbl_call(pf, 6, ctypes.c_long, [ctypes.c_wchar_p, ctypes.c_int], str(link), 1)  # Save
    finally:
        _vtbl_call(ptr, 2, ctypes.c_ulong, [])  # Release


def _query_interface(ptr, iid_text: str, out_ptr) -> None:
    import ctypes

    iid = _guid(iid_text)
    hr = _vtbl_call(
        ptr, 0, ctypes.c_long,
        [ctypes.POINTER(type(iid)), ctypes.POINTER(ctypes.c_void_p)],
        ctypes.byref(iid), out_ptr,
    )
    if hr != 0:
        raise RuntimeError("QueryInterface 失败，HRESULT=0x{:08X}".format(hr & 0xFFFFFFFF))


def _com_read(link: Path) -> str | None:
    import ctypes

    ptr = _com_create()
    try:
        pf = ctypes.c_void_p()
        _query_interface(ptr, "0000010b-0000-0000-C000-000000000046", ctypes.byref(pf))
        _vtbl_call(pf, 5, ctypes.c_long, [ctypes.c_wchar_p, ctypes.c_int], str(link), 0)  # Load
        buf = ctypes.create_unicode_buffer(1024)
        _vtbl_call(ptr, 3, ctypes.c_long, [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint],
                   buf, 1024, None, 0)  # GetPath
        return buf.value or None
    finally:
        _vtbl_call(ptr, 2, ctypes.c_ulong, [])


# ---------------------------------------------------------------- 回退实现

def _pywin32_write(link: Path, target: Path, workdir: Path) -> None:
    from win32com.client import Dispatch  # type: ignore

    shell = Dispatch("WScript.Shell")
    sc = shell.CreateShortCut(str(link))
    sc.Targetpath = str(target)
    sc.WorkingDirectory = str(workdir)
    sc.Save()


def _pwsh_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _run_pwsh(script: str) -> str:
    """用 -EncodedCommand 传输脚本，避开命令行中日韩字形的编码丢失。"""
    import base64

    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300])
    return proc.stdout or ""


def _powershell_write(link: Path, target: Path, workdir: Path) -> None:
    _run_pwsh(
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut({link});"
        "$s.TargetPath={target};$s.WorkingDirectory={wd};$s.Save()".format(
            link=_pwsh_quote(str(link)),
            target=_pwsh_quote(str(target)),
            wd=_pwsh_quote(str(workdir)),
        )
    )


def _powershell_read(link: Path) -> str | None:
    out = _run_pwsh(
        "$p=(New-Object -ComObject WScript.Shell).CreateShortcut({link}).TargetPath;"
        "[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($p))".format(
            link=_pwsh_quote(str(link))
        )
    ).strip()
    if not out:
        return None
    try:
        import base64

        return base64.b64decode(out).decode("utf-8", "replace") or None
    except Exception:
        return None


# ---------------------------------------------------------------- 主流程

def same_path(a: str, b: Path) -> bool:
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(str(b)))
    except Exception:
        return False


def create(link: Path, target: Path, workdir: Path) -> str:
    if sys.platform != "win32":
        raise SystemExit("快捷方式创建仅支持 Windows。当前平台：{}".format(sys.platform))
    if not target.exists():
        raise SystemExit("目标不存在：{}".format(target))

    link.parent.mkdir(parents=True, exist_ok=True)
    errors = []

    for label, writer in (
        ("ctypes COM", _com_write),
        ("pywin32", _pywin32_write),
        ("PowerShell", _powershell_write),
    ):
        try:
            writer(link, target, workdir)
            resolved = verify_lnk(link)
            if resolved and same_path(resolved, target):
                print("  创建方式：{}".format(label))
                print("  回读校验：{} → {}".format(link.name, resolved))
                return label
            if resolved:
                errors.append("{} 写入成功但目标不符：{}".format(label, resolved))
            else:
                errors.append("{} 写入后无法回读".format(label))
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            errors.append("{} 失败：{}".format(label, exc))

    raise SystemExit("三种方式均未成功：\n  " + "\n  ".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="为本地应用创建 Windows 快捷方式并回读校验",
        epilog="示例：python scripts/make_shortcut.py --target D:/学习/cxstudy/cxstudy.exe --name 学习通",
    )
    parser.add_argument("--target", default="", help="目标 exe 的绝对路径")
    parser.add_argument("--link", default="", help=".lnk 输出路径（默认桌面/<name>.lnk）")
    parser.add_argument("--name", default="学习通", help="快捷方式显示名（默认 学习通）")
    parser.add_argument("--workdir", default="", help="工作目录（默认目标 exe 所在目录）")
    parser.add_argument("--verify-only", action="store_true", help="只读回 .lnk 的目标，不创建")
    args = parser.parse_args()

    link = Path(args.link).expanduser() if args.link else default_link(args.name)

    if args.verify_only:
        resolved = verify_lnk(link)
        if resolved:
            print("{} → {}".format(link, resolved))
            return 0
        print("无法解析或文件不存在：{}".format(link))
        return 1

    if not args.target:
        parser.error("创建模式必须提供 --target")

    target = Path(args.target).expanduser().resolve()
    workdir = Path(args.workdir).expanduser().resolve() if args.workdir else target.parent

    print("创建快捷方式")
    print("  目标：{}".format(target))
    print("  工作目录：{}".format(workdir))
    print("  输出：{}".format(link))
    create(link, target, workdir)
    print("完成。双击该快捷方式即可启动，工作目录已固定，相对路径不会跑偏。")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
