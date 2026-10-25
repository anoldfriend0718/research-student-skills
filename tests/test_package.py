"""Offline publication and non-destructive installation checks."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicationTests(unittest.TestCase):
    def test_runtime_inventory_and_links(self):
        skills = sorted((ROOT / "skills").iterdir())
        self.assertEqual(len(skills), 10)
        for skill in skills:
            entry = skill / "SKILL.md"
            text = entry.read_text(encoding="utf-8")
            self.assertRegex(text, rf"(?m)^name: {re.escape(skill.name)}\s*$")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in target or target.startswith("#") or "<" in target:
                    continue
                self.assertTrue((skill / target.split("#")[0]).exists(), f"Broken link: {entry.relative_to(ROOT)} -> {target}")

    def test_no_profiles_secrets_backups_or_personal_paths(self):
        for path in (ROOT / "skills").rglob("*"):
            self.assertNotIn(path.name, {"runtime", "credentials.json", "school.json", ".env", "config.env"})
            self.assertNotIn(".bak", path.name)
            self.assertNotIn(".before-", path.name)
            if path.is_file() and path.suffix in {".md", ".py", ".mjs", ".js", ".ps1", ".sh", ".json", ".yaml", ".tsv", ".txt"}:
                text = path.read_text(encoding="utf-8-sig")
                # Upstream tests deliberately use /Users/u/ as a synthetic fixture.
                personal = r"C:\\Users\\[a-zA-Z0-9._-]+\\|/Users/(?!u/)[a-zA-Z0-9._-]+/|xuqh12"
                secrets = r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)"
                self.assertFalse(re.search(personal, text), f"Personal path: {path.relative_to(ROOT)}")
                self.assertFalse(re.search(secrets, text), f"Potential secret: {path.relative_to(ROOT)}")

    def test_python_syntax(self):
        for path in ROOT.rglob("*.py"):
            if ".git" not in path.parts:
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))

    def test_install_adds_dependencies_and_preserves_existing(self):
        with tempfile.TemporaryDirectory(prefix="student-skills-install-") as temp:
            destination = Path(temp) / "skills"
            args = [sys.executable, str(ROOT / "install.py"), "--destination", str(destination), "--only", "nature-downloader"]
            dry = subprocess.run(args + ["--dry-run"], capture_output=True, text=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(destination.exists())
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((destination / "web-access" / "SKILL.md").is_file())
            marker = destination / "nature-downloader" / "local-user-note.txt"
            marker.write_text("keep", encoding="utf-8")
            second = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(marker.read_text(), "keep")

    def test_snapshot_preserves_zero_missing_and_order(self):
        script = ROOT / "skills/chrome-form-filling/scripts/verify_snapshot.py"
        spec = importlib.util.spec_from_file_location("snapshot", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = [{"key": "a", "fields": {"metric": 0}}, {"key": "b", "fields": {"metric": None}}]
        changed = [{"key": "b", "fields": {"metric": ""}}, {"key": "a", "fields": {"metric": 0}}]
        differences = module.compare(expected, changed)
        self.assertTrue(any(d["problem"] == "order" for d in differences))
        self.assertTrue(any(d["problem"] == "value" for d in differences))

    def test_dependencies_are_auditable(self):
        data = json.loads((ROOT / "DEPENDENCIES.json").read_text(encoding="utf-8"))
        self.assertEqual(data["bundled_dependencies"]["nature-downloader"], ["web-access"])
        self.assertRegex(data["upstreams"]["web-access"]["commit"], r"^[0-9a-f]{40}$")
        self.assertIn("baihe26", (ROOT / "skills/nature-downloader/LICENSE").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
