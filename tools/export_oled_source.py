"""Create the small, editable OLED source set for a firmware bundle."""

import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "include/tiny18_oled_uart.h",
    "config/tiny18.keymap",
    "docs/tools/gen_svg.py",
    "docs/tools/make_oled_layers.py",
    "addons/oled/Makefile",
    "addons/oled/brightness.c",
    "addons/oled/brightness.h",
    "addons/oled/brightness_store.c",
    "addons/oled/brightness_store.h",
    "addons/oled/funconfig.h",
    "addons/oled/layers.h",
    "addons/oled/render.c",
    "addons/oled/render.h",
    "addons/oled/reserve_flash.py",
    "addons/oled/tiny18_layer.c",
)
EXTRA_FILES = {"tools/build_oled.py": "build_oled.py"}


def export(output):
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.mkdir(parents=True)
    try:
        for name in FILES:
            source = ROOT / name
            if not source.is_file():
                raise FileNotFoundError(f"Missing OLED source: {name}")
            destination = output / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        for source_name, destination_name in EXTRA_FILES.items():
            source = ROOT / source_name
            if not source.is_file():
                raise FileNotFoundError(f"Missing OLED build helper: {source_name}")
            shutil.copyfile(source, output / destination_name)
        shutil.copyfile(ROOT / "docs/oled-source-README.md", output / "README.md")
    except Exception:
        shutil.rmtree(output)
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = export(parser.parse_args().output)
    total = sum(path.stat().st_size for path in output.rglob("*"))
    count = len(FILES) + len(EXTRA_FILES) + 1
    print(f"Created {output} ({count} files, {total} bytes)")


if __name__ == "__main__":
    main()
