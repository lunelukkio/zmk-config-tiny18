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
    elif not 0 < len(data) <= 16 * 1024:
        raise ValueError("OLED firmware must fit in CH32V003 flash")


def package(version, keyboard, oled, licenses, output_root, source_commit,
            source_state, actions_run, build_date=None):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        raise ValueError("Use a version such as v0.3.1, not an Actions run ID")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("A complete source commit ID is required")
    if oled.suffix != ".bin":
        raise ValueError("Select an OLED .bin file, not a keyboard UF2 or ELF")
    sources = [keyboard / name for name in IMAGES[:3]] + [oled]
    for source in sources:
        validate_image(source)
    for required in ("Tiny18-MIT.txt", "inventory.json", "resolved-west.yml", "README.txt"):
        if not (licenses / required).is_file():
            raise ValueError(f"Missing license inventory item: {required}")
    try:
        for path in licenses.rglob("*"):
            if path.is_symlink():
                raise ValueError("License exports must contain regular files, not symlinks")
            if path.is_file():
                with path.open("rb") as stream:
                    stream.read(1)
    except OSError as error:
        raise ValueError(
            "License files are unreadable; re-export SDK licenses using cp -RL in Docker"
        ) from error
    target = output_root / version
    archive = output_root / f"tiny18-{version}.zip"
    if target.exists() or archive.exists():
        raise FileExistsError("The version already exists; existing bundles are never overwritten")
    target.mkdir(parents=True)
    for source, name in zip(sources, IMAGES):
        shutil.copyfile(source, target / name)
    shutil.copytree(licenses, target / "LICENSES")
    date = build_date or datetime.now(timezone.utc).isoformat(timespec="seconds")
    (target / "VERSION.txt").write_text(
        f"Tiny18 integrated firmware\nVersion: {version}\nBuild date (UTC): {date}\n"
        f"Keyboard source commit: {source_commit}\nOLED source commit: {source_commit}\n"
        f"Source state: {source_state}\nActions run ID: {actions_run}\n"
        "Review status: publication and hardware approval required\n"
        "Use both keyboard halves and the optional OLED from this same bundle.\n"
        "Third-party terms and dependency revisions are in LICENSES/.\n",
        encoding="utf-8",
    )
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
    parser.add_argument("--output-root", type=Path, default=Path("firmware"))
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-state", choices=("clean-tag", "local-review-worktree"), required=True)
    parser.add_argument("--actions-run", default="not run (local review build)")
    args = parser.parse_args()
    target, archive = package(
        args.version, args.keyboard, args.oled, args.licenses, args.output_root,
        args.source_commit, args.source_state, args.actions_run,
    )
    print(f"Created {target} and {archive}; nothing has been published")


if __name__ == "__main__":
    main()
