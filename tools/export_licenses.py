"""Export upstream license texts and source notices for release review.

This deliberately includes unused files/modules rather than claiming to be a
link-level license audit. A maintainer must review the resulting inventory.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEGAL_NAME = re.compile(r"license|licence|copying|copyright|notice", re.I)
NOTICE = re.compile(r"copyright|SPDX-License-Identifier|permission is hereby", re.I)
COMMENTS = re.compile(r"/\*.*?\*/|(?:^[ \t]*//[^\n]*\n)+", re.S | re.M)
SOURCE_SUFFIXES = {".c", ".h", ".cpp", ".hpp", ".s", ".S", ".rs"}


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def export_project(source, target):
    """Preserve tracked license files and complete copyright-bearing comments."""
    files = git(source, "ls-files", "--stage", "-z").split("\0")
    copied = []
    notices = []
    for entry in sorted(filter(None, files)):
        metadata, name = entry.split("\t", 1)
        # Git's mode is portable even when Windows cannot stat a Linux symlink.
        if metadata.split()[0] not in {"100644", "100755"}:
            continue
        path = source / name
        if not path.is_file() or path.is_symlink():
            continue
        if LEGAL_NAME.search(path.name) or "LICENSES" in path.parts:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            copied.append(name)
        elif path.suffix in SOURCE_SUFFIXES:
            data = path.read_bytes()
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError:
                content = data.decode("latin-1")
            blocks = [m.group() for m in COMMENTS.finditer(content)
                      if NOTICE.search(m.group())]
            if blocks:
                notices.append(f"\n--- {name} ---\n" + "\n".join(blocks))
    target.mkdir(parents=True, exist_ok=True)
    (target / "SOURCE-NOTICES.txt").write_text(
        "Copyright/license comments from upstream source files.\n"
        "Some files may not be linked into this firmware.\n" + "\n".join(notices),
        encoding="utf-8",
    )
    if not copied and not notices:
        raise ValueError(f"No upstream license or source notice found for {source.name}")
    return copied


def export_sdk_licenses(source, target):
    """Materialize license text, never copy Linux-specific link metadata."""
    try:
        files = [(p.relative_to(source), p.read_bytes())
                 for p in sorted(source.rglob("*")) if p.is_file()]
    except OSError as error:
        raise ValueError(
            "SDK licenses are unreadable on this host; extract them with cp -RL in Docker"
        ) from error
    if not files:
        raise ValueError("The SDK license directory is empty")
    copied = []
    for name, content in files:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        copied.append(name.as_posix())
    return copied


def sdk_inventory_entry(version, license_files):
    """Describe the SDK runtime separately from commit-pinned Git projects."""
    if not re.fullmatch(r"[0-9][0-9A-Za-z.+-]{0,63}", version):
        raise ValueError("Unsafe SDK version")
    return {
        "name": "zephyr-sdk-runtime",
        "version": version,
        "url": f"https://github.com/zephyrproject-rtos/sdk-ng/releases/tag/v{version}",
        "license_files": license_files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--sdk-licenses", type=Path, required=True)
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = args.workspace / "resolved-west.yml"
    projects = yaml.safe_load(manifest.read_text(encoding="utf-8"))["manifest"]["projects"]
    if not {"zmk", "zephyr", "zmk-rgbled-widget"}.issubset({p["name"] for p in projects}):
        parser.error("The resolved manifest is not a complete Tiny18 west workspace")
    if not args.sdk_licenses.is_dir() or not any(args.sdk_licenses.rglob("*")):
        parser.error("The SDK license directory is missing or empty")
    if args.output.exists():
        parser.error("Use a new output directory; existing license exports are not overwritten")
    args.output.mkdir(parents=True)
    shutil.copyfile(ROOT / "LICENSE", args.output / "Tiny18-MIT.txt")
    shutil.copyfile(manifest, args.output / "resolved-west.yml")
    inventory = []
    for project in projects:
        source = (args.workspace / project.get("path", project["name"])).resolve()
        source.relative_to(args.workspace.resolve())
        name = project["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("Unsafe project name")
        inventory.append({
            "name": name, "revision": git(source, "rev-parse", "HEAD"),
            "url": project["url"], "source_notices": "SOURCE-NOTICES.txt",
            "license_files": export_project(source, args.output / name),
        })
    oled = ROOT / "addons/oled/ch32fun"
    inventory.append({
        "name": "ch32fun", "revision": git(oled, "rev-parse", "HEAD"),
        "url": "https://github.com/cnlohr/ch32fun", "source_notices": "SOURCE-NOTICES.txt",
        "license_files": export_project(oled, args.output / "ch32fun"),
    })
    sdk_files = export_sdk_licenses(
        args.sdk_licenses, args.output / "zephyr-sdk-runtime"
    )
    try:
        inventory.append(sdk_inventory_entry(args.sdk_version, sdk_files))
    except ValueError as error:
        parser.error(str(error))
    (args.output / "inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output / "README.txt").write_text(
        "Tiny18 third-party license and attribution material\n\n"
        "This inventory preserves license texts and copyright-bearing C/Rust source\n"
        "comments from every resolved west module, ch32fun, and SDK runtime licenses.\n"
        "It includes unused components and is not a link-level license audit.\n"
        "An empty license_files list means the project has only embedded source\n"
        "notices; check the SPDX terms against the other included license texts.\n"
        "Git projects record a revision; zephyr-sdk-runtime records its version.\n"
        "The individual upstream terms apply; the entire firmware is not MIT-only.\n"
        "Review this inventory and the build/link maps before publishing binaries.\n",
        encoding="utf-8",
    )
    print(f"Exported {len(inventory)} inventory entries including SDK runtime licenses")


if __name__ == "__main__":
    main()
