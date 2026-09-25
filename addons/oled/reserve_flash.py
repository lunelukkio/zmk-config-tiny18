"""Reserve the last two CH32V003 flash pages for OLED settings."""

from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 16K"
if source.count(old) != 1:
    raise SystemExit("unexpected generated CH32V003 linker layout")
Path(sys.argv[2]).write_text(source.replace(old, "FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 16256"), encoding="utf-8")
