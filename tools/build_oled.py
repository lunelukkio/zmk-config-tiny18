"""Regenerate and build the OLED firmware from an extracted source package."""

from pathlib import Path
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR if (SCRIPT_DIR / "addons/oled").is_dir() else SCRIPT_DIR.parent
OLED = ROOT / "addons" / "oled"
DEPENDENCY = OLED / "ch32fun"
DEPENDENCY_URL = "https://github.com/cnlohr/ch32fun.git"
DEPENDENCY_REVISION = "50b6e591f466231bf3e3ea2c184b3c686e93d755"


def run(args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


def prepare_dependency():
    if DEPENDENCY.exists():
        if not (DEPENDENCY / ".git").exists():
            raise RuntimeError(f"Dependency path is not a Git checkout: {DEPENDENCY}")
        revision = subprocess.check_output(
            ["git", "-C", str(DEPENDENCY), "rev-parse", "HEAD"], text=True
        ).strip()
        if revision != DEPENDENCY_REVISION:
            raise RuntimeError(
                "Existing ch32fun checkout has another revision; "
                "preserve it and use a clean extracted OLED-SOURCE folder."
            )
        return

    DEPENDENCY.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "init", str(DEPENDENCY)])
    run(["git", "-C", str(DEPENDENCY), "remote", "add", "origin", DEPENDENCY_URL])
    run([
        "git", "-C", str(DEPENDENCY), "fetch", "--depth", "1", "origin",
        DEPENDENCY_REVISION,
    ])
    run(["git", "-C", str(DEPENDENCY), "checkout", "--detach", "FETCH_HEAD"])
    revision = subprocess.check_output(
        ["git", "-C", str(DEPENDENCY), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != DEPENDENCY_REVISION:
        raise RuntimeError("Fetched ch32fun revision does not match the pinned commit")


def main():
    run([sys.executable, "docs/tools/make_oled_layers.py"])
    prepare_dependency()
    run([
        "make", "OS=Windows_NT", "PREFIX=riscv-none-elf", "tiny18_layer.bin",
    ], cwd=OLED)
    print(f"Built {OLED / 'tiny18_layer.bin'}; nothing was flashed.")


if __name__ == "__main__":
    main()
