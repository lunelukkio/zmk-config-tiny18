"""Tests for the boundary between build output and distributable firmware."""

import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_firmware", ROOT / "tools/package_firmware.py")
package_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_tool)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.images = self.root / "images"
        self.images.mkdir()
        block = bytearray(512)
        struct.pack_into("<II", block, 0, 0x0A324655, 0x9E5D5157)
        struct.pack_into("<I", block, 508, 0x0AB16F30)
        for name in package_tool.IMAGES[:3]:
            (self.images / name).write_bytes(block)
        self.oled = self.images / "tiny18_layer.bin"
        self.oled.write_bytes(b"receiver")
        self.licenses = self.root / "LICENSE.txt"
        self.oled_source = self.root / "OLED-SOURCE"
        for name in (
                "README.md", "build_oled.py", "include/tiny18_oled_uart.h",
                "config/tiny18.keymap", "docs/tools/gen_svg.py",
                "docs/tools/make_oled_layers.py", "addons/oled/Makefile",
                "addons/oled/layers.h", "addons/oled/tiny18_layer.c",
                "addons/oled/render.c", "addons/oled/render.h"):
            path = self.oled_source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source", encoding="utf-8")
        self.output = self.root / "firmware"

    def bundle(self, version="v0.3.1"):
        self.licenses.write_text(
            f"Tiny18 firmware {version}: distribution licenses\n神沼三平太\n",
            encoding="utf-8",
        )
        return package_tool.package(version, self.images, self.oled, self.licenses,
                                    self.output, "a" * 40, "local-review-worktree", "not run",
                                    self.oled_source)

    def test_complete_bundle_has_checksums_and_only_intended_images(self):
        (self.images / "private.stl").write_bytes(b"must not be copied")
        target, archive = self.bundle()
        entries = (target / "SHA256SUMS").read_text().splitlines()
        self.assertEqual(len(entries), sum(1 for p in target.rglob("*") if p.is_file()) - 1)
        for line in entries:
            digest, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), digest)
        with zipfile.ZipFile(archive) as result:
            self.assertIn("v0.3.1/LICENSE.txt", result.namelist())
            self.assertIn("v0.3.1/README.md", result.namelist())
            self.assertIn("v0.3.1/OLED-SOURCE/docs/tools/make_oled_layers.py",
                          result.namelist())
            self.assertIn("v0.3.1/OLED-SOURCE/include/tiny18_oled_uart.h",
                          result.namelist())
            self.assertFalse(any("LICENSES/" in name for name in result.namelist()))
            self.assertFalse(any(name.endswith(".stl") for name in result.namelist()))
        self.assertIn("local-review-worktree", (target / "VERSION.txt").read_text())

    def test_existing_version_is_never_overwritten(self):
        target, _ = self.bundle()
        before = (target / "SHA256SUMS").read_bytes()
        with self.assertRaises(FileExistsError):
            self.bundle()
        self.assertEqual(before, (target / "SHA256SUMS").read_bytes())

    def test_missing_image_leaves_no_version_folder(self):
        (self.images / "tiny18-left.uf2").unlink()
        with self.assertRaises(FileNotFoundError):
            self.bundle()
        self.assertFalse(self.output.exists())

    def test_missing_licenses_leaves_no_version_folder(self):
        with self.assertRaises(ValueError):
            package_tool.package("v0.3.1", self.images, self.oled, self.licenses,
                                 self.output, "a" * 40, "local-review-worktree", "not run",
                                 self.oled_source)
        self.assertFalse(self.output.exists())

    def test_wrong_version_license_leaves_no_version_folder(self):
        self.licenses.write_text(
            "Tiny18 firmware v0.8.0: distribution licenses\n神沼三平太\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "another version"):
            package_tool.package("v0.3.1", self.images, self.oled, self.licenses,
                                 self.output, "a" * 40, "local-review-worktree", "not run",
                                 self.oled_source)
        self.assertFalse(self.output.exists())

    def test_bad_uf2_and_oversize_oled_are_rejected(self):
        (self.images / "tiny18-left.uf2").write_bytes(b"invalid")
        with self.assertRaises(ValueError):
            self.bundle()
        self.oled.write_bytes(b"x" * 16385)
        with self.assertRaises(ValueError):
            package_tool.validate_image(self.oled)

    def test_run_id_or_path_is_not_a_version(self):
        for version in ("35495107633", "../v0.3.1", "v0.3", "feature"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.bundle(version)
        self.assertFalse(self.output.exists())


class IntegrationTests(unittest.TestCase):
    def test_keyboard_ci_remains_independent_of_optional_oled(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/build.yml").read_text())
        self.assertEqual(workflow["jobs"]["build"]["uses"],
                         "zmkfirmware/zmk/.github/workflows/build-user-config.yml@v0.3.0")
        self.assertNotIn("needs", workflow["jobs"]["build"])

    def test_release_creates_only_a_draft_and_requires_both_builds(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
        job = workflow["jobs"]["draft"]
        self.assertEqual(set(job["needs"]), {"keyboard", "oled"})
        publish = next(s["run"] for s in job["steps"] if "gh release create" in s.get("run", ""))
        self.assertIn("--draft", publish)
        self.assertIn("--verify-tag", publish)
        self.assertNotIn("--draft=false", publish)

    def test_local_keyboard_targets_match_the_build_matrix(self):
        matrix = yaml.safe_load((ROOT / "build.yaml").read_text())["include"]
        script = (ROOT / "tools/build-keyboard.sh").read_text()
        self.assertEqual({m["artifact-name"] for m in matrix}, set(n[:-4] for n in package_tool.IMAGES[:3]))
        for target in matrix:
            self.assertIn(target["board"], script)
            self.assertIn(target["shield"], script)
            self.assertIn(target["artifact-name"] + ".uf2", script)
            if "snippet" in target:
                self.assertIn(target["snippet"], script)
            if "cmake-args" in target:
                for argument in target["cmake-args"].split():
                    self.assertIn(argument, script)

    def test_public_tools_have_no_private_project_or_host_path(self):
        for path in (ROOT / "docs/tools").glob("*"):
            if path.suffix not in {".py", ".html"}:
                continue
            content = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotIn("C:" + "\\Users\\", content)
                self.assertNotIn("t-" + "display", content)
                self.assertNotIn("TINY18_SITE_OUTPUT", content)


if __name__ == "__main__":
    unittest.main()
