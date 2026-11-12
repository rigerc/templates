"""No-network tests for the Copier skill updater."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_copier as mod  # noqa: E402


class UpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "skill"
        self.root.mkdir()
        (self.root / "SKILL.md").write_text(
            '---\nname: repo-copier\nmetadata:\n  version: "7.0.0"\n  copier_version: "9.0.0"\n---\n\nMy short guide.\n', encoding="utf-8"
        )
        (self.root / "VERSION").write_text("7.0.0\n")
        self.src = Path(self.temp.name) / "src"
        for filename, source in {**mod.DOCS, **mod.EXTRA}.items():
            path = self.src / source
            path.parent.mkdir(parents=True, exist_ok=True)
            contents = (
                "# Changelog\n\n## v9.19.1 (2026-10-13)\n\n### Fix\n\n- fixed a bug\n\n## v9.19.0 (2026-10-12)\n\n- feature\n"
                if filename == "CHANGELOG.md" else
                "MIT License\nCopyright (c) 2026 Copier contributors\n" if filename == "LICENSE" else
                f"# {filename}\nAn upstream document.\n"
            )
            path.write_text(contents, encoding="utf-8")

    def test_validates_versions(self):
        self.assertEqual(mod.validate_version("9.19.1"), "v9.19.1")
        self.assertEqual(mod.validate_version("v9.19.1"), "v9.19.1")
        for invalid in ("main", "v9.19.1-beta1", "9.19", "9.19.1/../foo"):
            with self.subTest(invalid=invalid), self.assertRaises(mod.UpdateError):
                mod.validate_version(invalid)

    def test_release_notes(self):
        text = (self.src / "CHANGELOG.md").read_text()
        self.assertIn("fixed a bug", mod.extract_changes(text, "v9.19.1"))
        with self.assertRaises(mod.UpdateError):
            mod.extract_changes(text, "v7.0.0")

    def test_updates_only_generated_content_and_is_idempotent(self):
        self.assertEqual(mod.update(self.root, "v9.19.1", self.src, check=False, dry_run=False), 0)
        skill = (self.root / "SKILL.md").read_text()
        self.assertIn('copier_version: "9.19.1"', skill)
        self.assertIn('version: "7.0.0"', skill)
        self.assertIn("My short guide.", skill)
        self.assertEqual((self.root / "VERSION").read_text(), "7.0.0\n")
        self.assertTrue((self.root / "reference/upstream/settings.md").is_file())
        self.assertTrue((self.root / "reference/upstream/LICENSE.copier").is_file())
        state = json.loads((self.root / mod.LOCK).read_text())
        self.assertEqual(state["copier_version"], "9.19.1")
        self.assertIn("reference/upstream/settings.md", state["files_sha256"])
        self.assertEqual(mod.update(self.root, "v9.19.1", self.src, check=True, dry_run=False), 0)
        self.assertEqual(mod.update(self.root, "v9.19.1", self.src, check=False, dry_run=False), 0)

    def test_check_and_dry_run_do_not_write(self):
        self.assertEqual(mod.update(self.root, "v9.19.1", self.src, check=True, dry_run=False), 1)
        self.assertEqual(mod.update(self.root, "v9.19.1", self.src, check=False, dry_run=True), 0)
        self.assertFalse((self.root / mod.LOCK).exists())
        self.assertIn('copier_version: "9.0.0"', (self.root / "SKILL.md").read_text())

    def test_missing_document_rolls_back(self):
        (self.src / "docs/settings.md").unlink()
        with self.assertRaises(mod.UpdateError):
            mod.update(self.root, "v9.19.1", self.src, check=False, dry_run=False)
        self.assertFalse((self.root / mod.LOCK).exists())
        self.assertIn('copier_version: "9.0.0"', (self.root / "SKILL.md").read_text())

    def test_missing_frontmatter_field_is_rejected(self):
        (self.root / "SKILL.md").write_text("---\nname: repo-copier\n---\n")
        with self.assertRaises(mod.UpdateError):
            mod.update(self.root, "v9.19.1", self.src, check=False, dry_run=False)

    def test_latest_tag_is_read_from_github(self):
        with patch.object(mod, "fetch", return_value=b'{"tag_name": "v9.19.1"}'):
            self.assertEqual(mod.latest_tag(), "v9.19.1")


if __name__ == "__main__":
    unittest.main()
