"""Keep embedded upstream notices as well as top-level license files."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("export_licenses", ROOT / "tools/export_licenses.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def staged_files(*names):
    return "".join(f"100644 {'a' * 40} 0\t{name}\0" for name in names)


class LicenseExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        self.source.mkdir()
        self.output = Path(self.temp.name) / "notices"

    def test_license_text_and_mid_file_notices_are_preserved(self):
        text = "Copyright example\nPermission text, unchanged.\n"
        (self.source / "LICENSE").write_text(text, encoding="utf-8")
        (self.source / "driver.c").write_text(
            "/* SPDX-License-Identifier: MIT */\nint first;\n"
            "/* Copyright example author.\n * Permission is hereby granted.\n */\nint second;\n",
            encoding="utf-8",
        )
        with patch.object(exporter, "git", return_value=staged_files("LICENSE", "driver.c")):
            result = exporter.export_project(self.source, self.output)
        self.assertEqual(result, ["LICENSE"])
        self.assertEqual((self.output / "LICENSE").read_text(), text)
        notices = (self.output / "SOURCE-NOTICES.txt").read_text()
        self.assertIn("SPDX-License-Identifier: MIT", notices)
        self.assertIn("Copyright example author.", notices)
        self.assertNotIn("int first;", notices)

    def test_nonstandard_filenames_in_licenses_directory_are_preserved(self):
        folder = self.source / "LICENSES"
        folder.mkdir()
        (folder / "BSD-3-Clause.txt").write_text("terms", encoding="utf-8")
        with patch.object(exporter, "git", return_value=staged_files("LICENSES/BSD-3-Clause.txt")):
            result = exporter.export_project(self.source, self.output)
        self.assertEqual(result, ["LICENSES/BSD-3-Clause.txt"])

    def test_missing_license_is_not_silently_reported_as_complete(self):
        with patch.object(exporter, "git", return_value=""), self.assertRaises(ValueError):
            exporter.export_project(self.source, self.output)

    def test_header_only_spdx_terms_remain_visible_for_review(self):
        (self.source / "driver.c").write_text(
            "/* Copyright example. SPDX-License-Identifier: Apache-2.0 */\n",
            encoding="utf-8",
        )
        with patch.object(exporter, "git", return_value=staged_files("driver.c")):
            self.assertEqual(exporter.export_project(self.source, self.output), [])
        self.assertIn("Apache-2.0", (self.output / "SOURCE-NOTICES.txt").read_text())

    def test_git_symlinks_are_skipped_before_windows_stat(self):
        (self.source / "LICENSE").write_text("terms", encoding="utf-8")
        entries = staged_files("LICENSE") + f"120000 {'b' * 40} 0\tunreadable.h\0"
        original = Path.is_file

        def check(path):
            if path.name == "unreadable.h":
                raise OSError("Linux symlink unavailable on this host")
            return original(path)

        with patch.object(exporter, "git", return_value=entries), patch.object(Path, "is_file", check):
            self.assertEqual(exporter.export_project(self.source, self.output), ["LICENSE"])

    def test_sdk_license_text_is_materialized_in_regular_files(self):
        folder = self.source / "crosstool-ng"
        folder.mkdir()
        text = b"Copyright example.\nLicense text, unchanged.\n"
        (folder / "LICENSE").write_bytes(text)
        copied = exporter.export_sdk_licenses(self.source, self.output)
        self.assertEqual((self.output / "crosstool-ng/LICENSE").read_bytes(), text)
        self.assertFalse((self.output / "crosstool-ng/LICENSE").is_symlink())
        self.assertEqual(copied, ["crosstool-ng/LICENSE"])

    def test_sdk_inventory_records_version_and_license_files(self):
        entry = exporter.sdk_inventory_entry(
            "0.16.9", ["crosstool-ng/LICENSE", "arm-zephyr-eabi/COPYING"]
        )
        self.assertEqual(entry["name"], "zephyr-sdk-runtime")
        self.assertEqual(entry["version"], "0.16.9")
        self.assertEqual(
            entry["url"],
            "https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v0.16.9",
        )
        self.assertNotIn("revision", entry)
        self.assertEqual(
            entry["license_files"],
            ["crosstool-ng/LICENSE", "arm-zephyr-eabi/COPYING"],
        )

    def test_sdk_inventory_rejects_unsafe_versions(self):
        for version in ("", "0.16.9 beta", "0.16.9/../../other"):
            with self.subTest(version=version), self.assertRaisesRegex(
                ValueError, "Unsafe SDK version"
            ):
                exporter.sdk_inventory_entry(version, ["LICENSE"])

    def test_unreadable_sdk_license_is_reported_before_writing(self):
        (self.source / "LICENSE").write_text("terms", encoding="utf-8")
        with patch.object(Path, "is_file", side_effect=OSError("Linux link")):
            with self.assertRaisesRegex(ValueError, "cp -RL"):
                exporter.export_sdk_licenses(self.source, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
