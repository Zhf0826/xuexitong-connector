#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓库自检：不联网、不碰用户配置，只验证 Skill 包的结构与脚本契约。

运行：python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import json
import py_compile
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
PRIVATE_PATH_RE = re.compile(r"[A-Za-z]:\\+Users\\+[^\\\s]+|/(?:home|Users)/[^/\s]+")


def read_frontmatter() -> dict:
    text = SKILL.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md 必须以 YAML frontmatter 开头")
    end = text.find("\n---", 4)
    if end == -1:
        raise AssertionError("frontmatter 未闭合")
    data = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        key, sep, value = line.partition(":")
        if sep:
            data[key.strip()] = value.strip().strip("\"'")
    data["_body"] = text[end + 4:]
    return data


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestFrontmatter(unittest.TestCase):
    def test_name_matches_folder(self):
        fm = read_frontmatter()
        self.assertRegex(fm["name"], NAME_RE)
        self.assertEqual(fm["name"], ROOT.name, "frontmatter.name 必须与目录名一致")

    def test_version_is_semver(self):
        self.assertRegex(read_frontmatter()["version"], SEMVER_RE)

    def test_description_is_specific(self):
        desc = read_frontmatter()["description"]
        self.assertGreater(len(desc), 40)
        self.assertLessEqual(len(desc), 1024)
        self.assertNotIn("<", desc)
        self.assertNotIn(">", desc)

    def test_no_unfinished_markers(self):
        body = read_frontmatter()["_body"]
        for marker in ("TODO", "FIXME", "TBD"):
            self.assertNotIn(marker, body, "SKILL.md 仍有未完成标记：" + marker)


class TestLinks(unittest.TestCase):
    def test_local_links_exist(self):
        body = read_frontmatter()["_body"]
        body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        targets = re.findall(r"\]\((?!https?://|#|mailto:)([^)]+)\)", body)
        self.assertTrue(targets, "SKILL.md 应至少引用一个本地资源")
        for raw in targets:
            target = raw.strip().split("#", 1)[0]
            self.assertTrue((ROOT / target).exists(), "本地链接失效：" + raw)

    def test_readme_links_exist(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for raw in re.findall(r"\]\((?!https?://|#|mailto:)([^)]+)\)", text):
            target = raw.strip().split("#", 1)[0]
            self.assertTrue((ROOT / target).exists(), "README 链接失效：" + raw)


class TestScripts(unittest.TestCase):
    def test_scripts_compile(self):
        for script in sorted((ROOT / "scripts").glob("*.py")):
            py_compile.compile(str(script), doraise=True)

    def test_help_exits_cleanly(self):
        for name in ("register_mcp.py", "check_env.py", "setup.py", "make_shortcut.py"):
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / name), "--help"],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(proc.returncode, 0, name + " --help 失败：" + proc.stderr[-400:])

    def test_entry_shape(self):
        reg = load_script("register_mcp.py")
        entry = reg.build_entry("C:/Python312/python.exe", {"CHAOXING_PHONE": "13800000000"})
        self.assertEqual(entry["type"], "stdio")
        self.assertEqual(entry["args"], ["-m", "xuexitong_mcp"])
        self.assertEqual(entry["command"], "C:/Python312/python.exe")

    def test_mask_hides_credentials(self):
        reg = load_script("register_mcp.py")
        masked = reg.mask("13800000000")
        self.assertNotIn("13800000000", masked)
        self.assertTrue(masked.startswith("138"))
        self.assertEqual(reg.mask(""), "")

    def test_load_missing_config_returns_empty(self):
        reg = load_script("register_mcp.py")
        self.assertEqual(reg.load_json(ROOT / "no-such-file.json"), {})


class TestOneClickInstaller(unittest.TestCase):
    def test_mask_phone(self):
        setup = load_script("setup.py")
        masked = setup.mask_phone("13800000000")
        self.assertNotIn("13800000000", masked)
        self.assertTrue(masked.startswith("138"))
        self.assertEqual(setup.mask_phone(""), "")

    def test_default_paths_are_user_scoped(self):
        setup = load_script("setup.py")
        self.assertEqual(setup.DEFAULT_MCP.name, "mcp.json")
        self.assertIn(".workbuddy", str(setup.DEFAULT_MCP))
        self.assertEqual(setup.DEFAULT_SERVER.name, "xuexitong-mcp")

    def test_installer_documents_manual_step(self):
        text = (ROOT / "scripts" / "setup.py").read_text(encoding="utf-8")
        self.assertIn("信任", text, "一键安装必须提示在客户端点信任这一步")


class TestShortcut(unittest.TestCase):
    def test_default_link_name(self):
        shortcut = load_script("make_shortcut.py")
        link = shortcut.default_link("学习通")
        self.assertEqual(link.suffix, ".lnk")
        self.assertEqual(link.stem, "学习通")

    def test_same_path_normalizes(self):
        shortcut = load_script("make_shortcut.py")
        self.assertTrue(shortcut.same_path(str(ROOT), ROOT))
        self.assertFalse(shortcut.same_path(str(ROOT), ROOT / "other"))

    def test_three_fallbacks_declared(self):
        text = (ROOT / "scripts" / "make_shortcut.py").read_text(encoding="utf-8")
        for marker in ("_com_write", "_pywin32_write", "_powershell_write"):
            self.assertIn(marker, text)


class TestSecurity(unittest.TestCase):
    def test_no_credential_files_committed(self):
        for name in ("config.json", "session_cookies.json", ".env"):
            self.assertFalse((ROOT / name).exists(), name + " 不应出现在仓库里")

    def test_gitignore_covers_secrets(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in ("config.json", "session_cookies.json", ".env"):
            self.assertIn(pattern, text)

    def test_no_secret_tokens(self):
        skip = {"tests", ".git", "dist", "__pycache__"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".yaml", ".yml", ".json"}:
                continue
            if skip & set(path.relative_to(ROOT).parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            self.assertIsNone(SECRET_RE.search(text), "疑似密钥：" + str(path.relative_to(ROOT)))
            self.assertIsNone(PRIVATE_PATH_RE.search(text), "疑似私人路径：" + str(path.relative_to(ROOT)))


class TestPackaging(unittest.TestCase):
    def test_agents_metadata(self):
        text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        fm = read_frontmatter()
        self.assertIn("interface:", text)
        self.assertIn("$" + fm["name"], text)

    def test_evals_manifest(self):
        data = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(data["skill"], read_frontmatter()["name"])
        self.assertGreaterEqual(len(data["cases"]), 3)
        self.assertTrue(any(c.get("trigger_expected") is False for c in data["cases"]))

    def test_reference_tool_count(self):
        text = (ROOT / "references" / "tools.md").read_text(encoding="utf-8")
        self.assertIn("16", text)
        for tool in ("login", "get_schedule", "get_homework_deadlines", "list_notices"):
            self.assertIn(tool, text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
