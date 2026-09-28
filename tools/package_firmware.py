"""Create a versioned local firmware bundle, never upload or flash it."""

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import shutil
import struct
import zipfile

IMAGES = ("tiny18-right.uf2", "tiny18-left.uf2", "settings-reset.uf2", "tiny18_layer.bin")


def validate_image(path):
    data = path.read_bytes()
    if path.suffix == ".uf2":
        if not data or len(data) % 512:
            raise ValueError(f"Invalid UF2 length: {path.name}")
        for offset in range(0, len(data), 512):
            if (struct.unpack_from("<II", data, offset) != (0x0A324655, 0x9E5D5157)
                    or struct.unpack_from("<I", data, offset + 508)[0] != 0x0AB16F30):
                raise ValueError(f"Invalid UF2 block: {path.name}")
    elif not 0 < len(data) <= 16 * 1024 - 128:
        raise ValueError("OLED firmware must leave two CH32V003 flash pages for settings")


def package(version, keyboard, oled, licenses, output_root, source_commit,
            source_state, actions_run, oled_source, build_date=None,
            version_file=None, readme=None):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        raise ValueError("Use a version such as v0.3.1, not an Actions run ID")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("A complete source commit ID is required")
    if oled.suffix != ".bin":
        raise ValueError("Select an OLED .bin file, not a keyboard UF2 or ELF")
    sources = [keyboard / name for name in IMAGES[:3]] + [oled]
    for source in sources:
        validate_image(source)
    try:
        if not licenses.is_file() or licenses.is_symlink():
            raise ValueError("A regular LICENSE.txt file is required")
        license_text = licenses.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("LICENSE.txt is unreadable") from error
    if (not license_text.splitlines()
            or f"Tiny18 firmware {version}:" not in license_text.splitlines()[0]
            or "神沼三平太" not in license_text
            or "needs final review" in license_text):
        raise ValueError("LICENSE.txt is incomplete or for another version")
    source_files = (
        "README.md", "build_oled.py", "include/tiny18_oled_uart.h",
        "config/tiny18.keymap", "docs/tools/gen_svg.py",
        "docs/tools/make_oled_layers.py", "addons/oled/Makefile",
        "addons/oled/layers.h", "addons/oled/tiny18_layer.c",
        "addons/oled/render.c", "addons/oled/render.h",
    )
    if not oled_source.is_dir() or any(
            not (oled_source / name).is_file() for name in source_files):
        raise ValueError("The editable OLED source package is incomplete")
    if (oled_source / "addons/oled/ch32fun").exists():
        raise ValueError("Keep the large ch32fun dependency out of the source package")
    readme = readme or Path(__file__).resolve().parents[1] / "docs/distribution-README.md"
    if not readme.is_file() or readme.is_symlink():
        raise ValueError("A regular distribution README.md is required")
    source_entries = list(oled_source.rglob("*"))
    if any(path.is_symlink() for path in source_entries):
        raise ValueError("The editable OLED source package cannot contain symlinks")
    if sum(path.stat().st_size for path in source_entries if path.is_file()) > 512_000:
        raise ValueError("The editable OLED source package exceeds its size limit")
    if version_file is not None:
        existing_metadata = version_file.read_text(encoding="utf-8")
        if f"Version: {version}\n" not in existing_metadata:
            raise ValueError("VERSION.txt is for another version")
    target = output_root / version
    archive = output_root / f"tiny18-{version}.zip"
    if target.exists() or archive.exists():
        raise FileExistsError("The version already exists; existing bundles are never overwritten")
    target.mkdir(parents=True)
    for source, name in zip(sources, IMAGES):
        shutil.copyfile(source, target / name)
    shutil.copyfile(licenses, target / "LICENSE.txt")
    shutil.copyfile(readme, target / "README.md")
    shutil.copytree(oled_source, target / "OLED-SOURCE")
    date = build_date or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if version_file is not None:
        metadata = existing_metadata.replace(
            "Third-party terms and dependency revisions are in LICENSES/.",
            "Third-party terms are in LICENSE.txt.",
        )
        if "Editable OLED sources" not in metadata:
            metadata += "Editable OLED sources and build instructions are in OLED-SOURCE/.\n"
    else:
        metadata = (
            f"Tiny18 integrated firmware\nVersion: {version}\nBuild date (UTC): {date}\n"
            f"Keyboard source commit: {source_commit}\nOLED source commit: {source_commit}\n"
            f"Source state: {source_state}\nActions run ID: {actions_run}\n"
            "Review status: publication and hardware approval required\n"
            "Use both keyboard halves and the optional OLED from this same bundle.\n"
            "Third-party terms are in LICENSE.txt.\n"
            "Editable OLED sources and build instructions are in OLED-SOURCE/.\n"
        )
    (target / "VERSION.txt").write_text(metadata, encoding="utf-8")
    paths = sorted(p for p in target.rglob("*") if p.is_file())
    (target / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(target).as_posix()}\n"
        for p in paths
    ), encoding="utf-8")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(p for p in target.rglob("*") if p.is_file()):
            bundle.write(path, f"{version}/{path.relative_to(target).as_posix()}")
    return target, archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--keyboard", type=Path, required=True)
    parser.add_argument("--oled", type=Path, default=Path("addons/oled/tiny18_layer.bin"))
    parser.add_argument("--licenses", type=Path, required=True)
    parser.add_argument("--oled-source", type=Path, required=True)
    parser.add_argument("--readme", type=Path, default=Path("docs/distribution-README.md"))
    parser.add_argument("--output-root", type=Path, default=Path("firmware"))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-state", choices=("clean-tag", "local-review-worktree"), required=True)
    parser.add_argument("--actions-run", default="not run (local review build)")
    parser.add_argument("--version-file", type=Path)
    args = parser.parse_args()
    target, archive = package(
        args.version, args.keyboard, args.oled, args.licenses, args.output_root,
        args.source_commit, args.source_state, args.actions_run,
        args.oled_source,
        version_file=args.version_file,
        readme=args.readme,
    )
    print(f"Created {target} and {archive}; nothing has been published")


if __name__ == "__main__":
    main()
