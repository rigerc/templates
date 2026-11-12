"""Tests for skill helper scripts; no cargo/Rust installation required."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from validate_template import Checker  # noqa: E402


class ValidatorTests(unittest.TestCase):
    def check(self, root: Path):
        checker = Checker(root)
        checker.check()
        return checker.diagnostics

    def test_every_bundled_template_passes_strict(self):
        for kind in ("bin", "lib", "workspace"):
            with self.subTest(kind=kind):
                result = self.check(SKILL_ROOT / "assets" / f"{kind}-template")
                self.assertEqual([], result)

    def test_starter_manifest_toml_after_basic_variable_substitution(self):
        # Illustrative static substitution only; not a replacement for cargo-generate.
        for kind in ("bin", "lib", "workspace"):
            root = SKILL_ROOT / "assets" / f"{kind}-template"
            for manifest in root.rglob("Cargo.toml.liquid"):
                with self.subTest(kind=kind, manifest=str(manifest)):
                    rendered = (manifest.read_text()
                        .replace("{{ project-name }}", "demo-project")
                        .replace("{{ crate_name }}", "demo_project")
                        .replace("{{ rust_edition }}", "2021"))
                    parsed = tomllib.loads(rendered)
                    self.assertTrue("package" in parsed or "workspace" in parsed)

    def test_missing_hook_and_glob_ignore_report_errors(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "cargo-generate.toml").write_text('''
[template]
cargo_generate_version = ">=0.26.0"
ignore = ["*.txt"]
[hooks]
pre = ["missing.rhai"]
''')
            (root / "Cargo.toml").write_text('[package]\nname = "test"\nversion = "0.1.0"\n')
            msgs = [d.message for d in self.check(root) if d.level == "ERROR"]
            self.assertTrue(any("glob" in s for s in msgs))
            self.assertTrue(any("Hook script not found" in s for s in msgs))

    def test_unresolved_placeholders_and_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "cargo-generate.toml").write_text('[template]\ncargo_generate_version=">=0.26.0"\n')
            (root / "Cargo.toml").write_text('foo = "{{ undefined }}"')
            (root / "Cargo.toml.liquid").write_text('foo = "bar"')
            diagnostics = self.check(root)
            self.assertTrue(any("Potentially undefined" in d.message for d in diagnostics))
            self.assertTrue(any("collides" in d.message for d in diagnostics))

    def test_github_raw_tag_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "cargo-generate.toml").write_text('[template]\ncargo_generate_version=">=0.26.0"\n')
            (root / "Cargo.toml.liquid").write_text('[package]\nname="{{project-name}}"\n')
            (root / "ci.yml.liquid").write_text('key: {% raw %}${{ github.ref }}{% endraw %}\n')
            self.assertEqual([], self.check(root))

    def test_choice_default_must_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "cargo-generate.toml").write_text('''
[template]
cargo_generate_version = ">=0.26.0"
[placeholders]
mode = { type="string", prompt="Mode?", choices=["safe"], default="fast" }
''')
            (root / "Cargo.toml").write_text('[package]\nname="demo"\n')
            self.assertTrue(any("absent from choices" in d.message for d in self.check(root)))

    def test_wrong_template_section_type_never_crashes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "cargo-generate.toml").write_text('template = ["not a table"]\n')
            (root / "Cargo.toml").write_text('[package]\nname="demo"\n')
            self.assertTrue(any("Must be a TOML table" in d.message for d in self.check(root)))


class ScaffoldTests(unittest.TestCase):
    def test_scaffold_all_kinds_and_no_overwrite(self):
        script = SKILL_ROOT / "scripts" / "scaffold_template.py"
        for kind in ("bin", "lib", "workspace"):
            with tempfile.TemporaryDirectory() as td:
                dest = Path(td) / "new-template"
                result = subprocess.run([sys.executable, str(script), str(dest), "--kind", kind], capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertTrue((dest / "cargo-generate.toml").exists())
                self.assertTrue((dest / ".github" / "workflows" / "ci.yml").exists())
                self.assertEqual([], ValidatorTests().check(dest))
                repeat = subprocess.run([sys.executable, str(script), str(dest), "--kind", kind], capture_output=True, text=True)
                self.assertNotEqual(0, repeat.returncode)
                self.assertIn("Refusing to overwrite", repeat.stderr)


if __name__ == "__main__":
    unittest.main()
