"""Generate the label data for Tiny18's learning display.

The output is a C header consumed by addons/oled. Labels
come from gen_svg.py, the existing single parser for tiny18.keymap, so the
training display cannot silently drift from the firmware layout.

The display shows one state at a time: the highest active layer plus the
modifiers held.  Shift swaps a plain symbol or digit for what the US layout
sends (1 becomes !, - becomes _). Letters are always drawn upper case, the
same as their key names on the board and in the printed diagram; the display
does not report whether the host is about to receive a lower or upper case
letter. Ctrl puts a caret in front (^x or ^X), Alt and GUI
only show in the title.  Eight layers times Shift times Ctrl is 32 states, far
too many to keep as 1 KB bitmaps in the receiver's 16 KB flash, so the header
carries text: a glyph table for the 3x5 pixel font below, the box layout, and
one label set per distinct state.  The receiver's render.c draws them with the
same rules draw_state() uses here, so --preview shows what the OLED will show.

Three layouts:

- 3x3 (default since 2026-09-17, display v0.1.0): every key in three rows of
  three per half, at the 12 layout's box width: the two rows of 12, then the
  thumbs with the little-finger keys in the corners.
- 12: the twelve keys without a hold role, positions 0 1 2 / 7 8 9 on the
  left and 3 4 5 / 10 11 12 on the right, as two rows of six.  The default
  until 2026-09-17.
- 18: every key, drawn where it sits on the board: three on top, four on the
  home row and two thumbs per half.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image

import gen_svg


WIDTH = 128
HEIGHT = 64
# Titles carry no layer number: the name alone says where you are, so it has
# to stand on its own. The two held pages are named after what they put under
# the fingers, the way ZXCV already was.
LAYER_TITLES = ("TEXT", "BLUETOOTH", "AI", "NUMPAD", "FUNCTION", "GAME",
                "1234567890-=", "ZXCV")
DEFAULT_OUTPUT = gen_svg.ROOT / "addons" / "oled" / "layers.h"

# State byte, shared with layer_uart.c and render.c: layer in bits 0-2, then
# one bit per modifier.  Bit 7 stays clear so the receiver can reject noise.
STATE_SHIFT = 0x08
STATE_CTRL = 0x10
STATE_ALT = 0x20
STATE_GUI = 0x40
MOD_SUFFIX = ((STATE_SHIFT, "S"), (STATE_CTRL, "C"), (STATE_ALT, "A"), (STATE_GUI, "G"))
# Label sets are keyed by layer, Shift and Ctrl only; Alt and GUI change the
# title, not the keys.
LABEL_STATES = 32

# 3x5 pixel font, five rows of three cells, '#' lit. Lowercase letters use the
# same cell and scale, with a shorter body where the letter has no ascender.
GLYPHS = {
    "A": ".#. #.# ### #.# #.#", "B": "##. #.# ##. #.# ##.", "C": ".## #.. #.. #.. .##",
    "D": "##. #.# #.# #.# ##.", "E": "### #.. ##. #.. ###", "F": "### #.. ##. #.. #..",
    "G": ".## #.. #.# #.# .##", "H": "#.# #.# ### #.# #.#", "I": "### .#. .#. .#. ###",
    "J": "..# ..# ..# #.# .#.", "K": "#.# #.# ##. #.# #.#", "L": "#.. #.. #.. #.. ###",
    "M": "#.# ### ### #.# #.#", "N": "##. #.# #.# #.# #.#", "O": ".#. #.# #.# #.# .#.",
    "P": "##. #.# ##. #.. #..", "Q": ".#. #.# #.# ##. .##", "R": "##. #.# ##. #.# #.#",
    "S": ".## #.. .#. ..# ##.", "T": "### .#. .#. .#. .#.", "U": "#.# #.# #.# #.# ###",
    "V": "#.# #.# #.# #.# .#.", "W": "#.# #.# ### ### #.#", "X": "#.# #.# .#. #.# #.#",
    "Y": "#.# #.# .#. .#. .#.", "Z": "### ..# .#. #.. ###",
    "a": "... .## #.# #.# .##", "b": "#.. #.. ##. #.# ##.", "c": "... .## #.. #.. .##",
    "d": "..# ..# .## #.# .##", "e": "... .#. #.# ##. .##", "f": ".## .#. ### .#. .#.",
    "g": "... .## #.# .## ##.", "h": "#.. #.. ##. #.# #.#", "i": ".#. ... .#. .#. .#.",
    "j": "..# ... ..# #.# .#.", "k": "#.. #.# ##. #.# #.#", "l": "##. .#. .#. .#. ..#",
    "m": "... #.# ### #.# #.#", "n": "... ##. #.# #.# #.#", "o": "... .#. #.# #.# .#.",
    "p": "... ##. #.# ##. #..", "q": "... .## #.# .## ..#", "r": "... #.# ##. #.. #..",
    "s": "... .## ##. ..# ##.", "t": ".#. ### .#. .#. ..#", "u": "... #.# #.# #.# .##",
    "v": "... #.# #.# #.# .#.", "w": "... #.# #.# ### #.#", "x": "... #.# .#. .#. #.#",
    "y": "... #.# .## ..# ##.", "z": "... ### ..# #.. ###",
    "0": "### #.# #.# #.# ###", "1": ".#. ##. .#. .#. ###", "2": "##. ..# .#. #.. ###",
    "3": "### ..# .## ..# ###", "4": "#.# #.# ### ..# ..#", "5": "### #.. ##. ..# ##.",
    "6": ".## #.. ### #.# ###", "7": "### ..# .#. .#. .#.", "8": "### #.# ### #.# ###",
    "9": "### #.# ### ..# ##.",
    " ": "... ... ... ... ...", "/": "..# ..# .#. #.. #..", "-": "... ... ### ... ...",
    "+": "... .#. ### .#. ...", "=": "... ### ... ### ...", ".": "... ... ... ... .#.",
    ",": "... ... ... .#. #..", "'": ".#. .#. ... ... ...", "`": "#.. .#. ... ... ...",
    ";": "... .#. ... .#. #..", ":": "... .#. ... .#. ...", "[": "##. #.. #.. #.. ##.",
    "]": ".## ..# ..# ..# .##", "\\": "#.. #.. .#. ..# ..#", "(": ".#. #.. #.. #.. .#.",
    ")": ".#. ..# ..# ..# .#.", "?": "### ..# .## ... .#.", "<": "..# .#. #.. .#. ..#",
    ">": "#.. .#. ..# .#. #..", "^": ".#. #.# ... ... ...", "#": "#.# ### #.# ### #.#",
    "!": ".#. .#. .#. ... .#.", '"': "#.# #.# ... ... ...", "~": "... .## ##. ... ...",
    "*": "#.# .#. #.# ... ...", "&": ".#. #.# .#. #.# .##", "@": ".#. #.# ### #.. .##",
    "$": ".## ##. .#. .## ##.", "%": "#.. ..# .#. #.. ..#",
    "{": ".## .#. ##. .#. .##", "}": "##. .#. .## .#. ##.", "|": ".#. .#. .#. .#. .#.",
    "_": "... ... ... ... ###",
    "←": ".#. #.. ### #.. .#.", "→": ".#. ..# ### ..# .#.",
    "↑": ".#. #.# .#. .#. .#.", "↓": ".#. .#. .#. #.# .#.",
    "⏎": "..# ..# #.# ### .#.", "—": "... ... ### ... ...",
}
GLYPH_W = 3
GLYPH_H = 5
GLYPH_GAP = 1

# What the US layout sends for a plain key while Shift is held.  Keypad
# digits are not in here on purpose: they are looked up by binding, and
# "&kp KP_N1" never changes.
SHIFTED = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&", "8": "*",
    "9": "(", "0": ")", "-": "_", "=": "+", "[": "{", "]": "}", "\\": "|", ";": ":",
    "'": '"', ",": "<", ".": ">", "/": "?", "`": "~",
}
PLAIN_KP = re.compile(r"&kp (?!KP_)[A-Z0-9_]+$")

# gen_svg labels that do not fit a key box as they are.  Applied per line
# after the label is split, longest key first so "Space" wins over "Sp".
SHORT = {
    "BkSp": "BS", "Space": "SPC", "Enter": "ENT", "Shift": "SFT", "Ctrl": "CTL",
    "Esc": "ESC", "Tab": "TAB", "Del": "DEL", "PrtSc": "PRT", "PgUp": "PGU", "PgDn": "PGD",
    "NumLk": "NUM", "GUI": "GUI", "Alt": "ALT", "R Ctrl": "RCT", "R Alt": "RAL",
    "CapsLk": "CAP", "ScrLk": "SCR", "Pause": "PSE", "Menu": "MNU",
    "数字": "NUM", "を開く": "HLD", "BT ": "BT",
}


def glyph_key(char: str) -> str:
    return char if char in GLYPHS else char.upper()


def text_width(text: str, scale: int) -> int:
    return (len(text) * (GLYPH_W + GLYPH_GAP) - GLYPH_GAP) * scale if text else 0


def draw_text(image: Image.Image, x: int, y: int, text: str, scale: int) -> None:
    """Draw text in the pixel font with its top-left corner at (x, y)."""
    pixels = image.load()
    for char in text:
        rows = GLYPHS.get(glyph_key(char), GLYPHS["?"]).split()
        for row, cells in enumerate(rows):
            for col, cell in enumerate(cells):
                if cell != "#":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        pixels[x + col * scale + dx, y + row * scale + dy] = 1
        x += (GLYPH_W + GLYPH_GAP) * scale


def label_lines(binding: str, max_chars: int) -> list[str]:
    """Up to two lines of at most max_chars characters for one binding."""
    label, category = gen_svg.label(binding)
    if binding[1:] in gen_svg.MACRO_TEXT:
        # A macro types a slash command: keep the command's first letters on
        # one line, and whatever gen_svg put on the second - the Enter mark,
        # back when the macros sent one - on the next.
        lines = label.split("\n")
        name = lines[0].lstrip("/")
        first = ("/" + name[:max_chars - 1]) if max_chars >= 4 else name[:max_chars]
        return [first] + lines[1:2]
    if label.startswith("Ctrl+Shift+"):
        return ["C+S", shorten(label[len("Ctrl+Shift+"):], max_chars)]
    if label.startswith("Ctrl+"):
        return ["CTL", shorten(label[len("Ctrl+"):], max_chars)]
    lines = [shorten(line, max_chars) for line in label.split("\n")[:2]]
    return lines or ["-"]


def shorten(line: str, max_chars: int) -> str:
    for long, short in sorted(SHORT.items(), key=lambda item: -len(item[0])):
        line = line.replace(long, short)
    return line[:max_chars]


def state_lines(binding: str, shift: bool, ctrl: bool, max_chars: int,
                *, letter_case: bool = False) -> list[str]:
    """The label for one key while the given modifiers are held."""
    # A mod-morph answers the Shift question itself: it sends a different key,
    # without the Shift, so the box shows that key rather than a shifted one.
    morphed = shift and binding != gen_svg.shifted(binding)
    if morphed:
        binding = gen_svg.shifted(binding)
    # Every label is upper case, including a text-entry tap: the display
    # names a key, and does not report the lower/upper case the host types.
    # letter_case is otherwise unused now but stays so a future need to tell
    # a bare letter tap from an abbreviation does not have to re-plumb this.
    lines = [line.upper() for line in label_lines(binding, max_chars)]
    if letter_case:
        lines = gen_svg.format_letter_label("\n".join(lines), "upper").split("\n")
    _, category = gen_svg.label(binding)
    if shift and not morphed and len(lines) == 1 and PLAIN_KP.match(binding) and lines[0] in SHIFTED:
        lines = [SHIFTED[lines[0]]]
    # Only plain keys take the caret: a chorded combo or a macro sent with
    # Ctrl held is not something the box can describe in four characters.
    if ctrl and category == "key" and len(lines) == 1 and 0 < len(lines[0]) < max_chars:
        lines = ["^" + lines[0]]
    return lines


# Layout: one (position, x, y) per drawn key, the box size and the label
# length limit.  Nothing is drawn between the halves; the gap does that.


def layout_12() -> tuple[list[tuple[int, int, int]], int, int, int]:
    # 18 px boxes on a 20 px step, with a 10 px channel down the middle: the
    # two hands read apart at a glance. One pixel is left clear on all four
    # sides, because a panel whose columns sit a pixel off would otherwise
    # shave the outermost border off one side and leave a gap on the other.
    cells = []
    for row, positions in enumerate(((0, 1, 2, 3, 4, 5), (7, 8, 9, 10, 11, 12))):
        for col, position in enumerate(positions):
            cells.append((position, 1 + col * 20 + (8 if col >= 3 else 0), 14 + row * 25))
    return cells, 18, 24, 4


def layout_18() -> tuple[list[tuple[int, int, int]], int, int, int]:
    # (position, column, row) on an 8-column grid, right half after a gap.
    grid = [(0, 1, 0), (1, 2, 0), (2, 3, 0), (3, 4, 0), (4, 5, 0), (5, 6, 0),
            (6, 0, 1), (7, 1, 1), (8, 2, 1), (9, 3, 1),
            (10, 4, 1), (11, 5, 1), (12, 6, 1), (13, 7, 1),
            (14, 2, 2), (15, 3, 2), (16, 4, 2), (17, 5, 2)]
    cells = [(position, col * 15 + (8 if col >= 4 else 0), 12 + row * 17) for position, col, row in grid]
    return cells, 14, 16, 3


def layout_3x3() -> tuple[list[tuple[int, int, int]], int, int, int]:
    # The 12 layout's columns with a third row, so all 18 keys show at the
    # width that keeps four-character labels and doubled letters. The thumbs
    # sit under the keys they are under on the board (14 and 15 under 8 and
    # 9, 16 and 17 under 10 and 11), and the free corners take the
    # little-finger keys, 6 below 7 and 13 below 12. Boxes are 16 px tall on
    # a 17 px step from row 13, two rows clear of the title: the last border
    # lands on row 62, keeping the clear pixel at the bottom.
    cells = []
    for row, positions in enumerate(((0, 1, 2, 3, 4, 5), (7, 8, 9, 10, 11, 12), (6, 14, 15, 16, 17, 13))):
        for col, position in enumerate(positions):
            cells.append((position, 1 + col * 20 + (8 if col >= 3 else 0), 13 + row * 17))
    return cells, 18, 16, 4


LAYOUTS = {"12": layout_12, "18": layout_18, "3x3": layout_3x3}


def title_text(layer: int, state: int) -> str:
    title = LAYER_TITLES[layer]
    flags = "".join(letter for bit, letter in MOD_SUFFIX if state & bit)
    return title + (" +" + flags if flags else "")


def draw_state(labels: list[list[str]], layer: int, state: int, keys: str) -> Image.Image:
    """One screen, drawn exactly the way render.c draws it on the OLED."""
    image = Image.new("1", (WIDTH, HEIGHT), 0)
    pixels = image.load()
    title = title_text(layer, state)
    assert text_width(title, 2) <= WIDTH, f"title {title!r} does not fit"
    draw_text(image, (WIDTH - text_width(title, 2)) // 2, 1, title, 2)
    # No rules anywhere: the title sits above a band of empty rows, and the
    # channel between the halves does the dividing. Lines next to the boxes
    # only added edges for the eye to trip over (2026-09-16).

    cells, box_w, box_h, _ = LAYOUTS[keys]()
    for (position, x, y), lines in zip(cells, labels):
        for dx in range(box_w):
            pixels[x + dx, y] = 1
            pixels[x + dx, y + box_h - 1] = 1
        for dy in range(box_h):
            pixels[x, y + dy] = 1
            pixels[x + box_w - 1, y + dy] = 1
        # A short single label is doubled so a letter reads from arm's length.
        scale = 2 if len(lines) == 1 and text_width(lines[0], 2) <= box_w - 4 else 1
        line_h = GLYPH_H * scale
        top = y + (box_h - (line_h * len(lines) + (len(lines) - 1))) // 2
        for index, line in enumerate(lines):
            width = text_width(line, scale)
            assert width <= box_w - 2, f"label {line!r} is {width}px wide for a {box_w}px box (layer {layer}, position {position})"
            draw_text(image, x + (box_w - width) // 2, top + index * (line_h + 1), line, scale)
    return image


def label_sets(layers: list, keys: str) -> tuple[list[list[list[str]]], list[int]]:
    """Distinct label sets and, per state, which set it shows."""
    cells, _, _, max_chars = LAYOUTS[keys]()
    # A &trans key shows what it falls through to. Every transparent key in
    # this keymap ends up at the text-entry binding, so that is what the
    # display draws for it.
    base = layers[0][1]
    sets: list[list[list[str]]] = []
    state_set = []
    for state in range(LABEL_STATES):
        layer, shift, ctrl = state & 7, bool(state & STATE_SHIFT), bool(state & STATE_CTRL)
        bindings = [base[position] if binding == "&trans" else binding for position, binding in enumerate(layers[layer][1])]
        letter_case = layers[layer][0] in gen_svg.LETTER_CASE_LAYERS
        labels = [state_lines(bindings[position], shift, ctrl, max_chars,
                              letter_case=letter_case) for position, _, _ in cells]
        if labels not in sets:
            sets.append(labels)
        state_set.append(sets.index(labels))
    return sets, state_set


def glyph_table(sets: list[list[list[str]]]) -> dict[str, int]:
    """Glyph index per character used anywhere; index 0 means end of text."""
    used = set(" +SCAG")
    for title in LAYER_TITLES:
        used.update(title)
    for labels in sets:
        for lines in labels:
            for line in lines:
                used.update(glyph_key(char) for char in line)
    used.update("01234567")
    missing = used.difference(GLYPHS)
    assert not missing, f"missing glyphs: {sorted(missing)}"
    return {char: index for index, char in enumerate(sorted(used), start=1)}


def glyph_rows(char: str) -> list[int]:
    """Five bytes per glyph: bit 2 is the left cell of the row."""
    rows = []
    for cells in GLYPHS.get(glyph_key(char), GLYPHS["?"]).split():
        value = 0
        for col, cell in enumerate(cells):
            if cell == "#":
                value |= 1 << (2 - col)
        rows.append(value)
    return rows


def encode(text: str, glyphs: dict[str, int], length: int) -> list[int]:
    codes = [glyphs[glyph_key(char)] for char in text]
    assert len(codes) <= length, f"{text!r} is longer than {length}"
    return codes + [0] * (length - len(codes))


def write_header(output: Path, keys: str, sets: list[list[list[str]]], state_set: list[int]) -> None:
    cells, box_w, box_h, max_chars = LAYOUTS[keys]()
    glyphs = glyph_table(sets)
    title_chars = max(len(name) for name in LAYER_TITLES)
    lines = [
        "// Copyright (c) 2026 lunelukkio",
        "// SPDX-License-Identifier: MIT",
        "// Auto-generated by docs/tools/make_oled_layers.py. Do not edit by hand.",
        f"// Layout: {keys} keys. Regenerate after every keymap change.",
        "#ifndef TINY18_LAYERS_H",
        "#define TINY18_LAYERS_H",
        "",
        "#include <stdint.h>",
        "",
        f"#define TINY18_LAYER_COUNT {len(LAYER_TITLES)}",
        f"#define TINY18_KEY_COUNT {len(cells)}",
        f"#define TINY18_LABEL_STATES {LABEL_STATES}",
        f"#define TINY18_LABEL_SETS {len(sets)}",
        f"#define TINY18_LABEL_CHARS {max_chars}",
        f"#define TINY18_TITLE_CHARS {title_chars}",
        f"#define TINY18_GLYPH_COUNT {len(glyphs) + 1}",
        f"#define TINY18_BOX_W {box_w}",
        f"#define TINY18_BOX_H {box_h}",
        "",
        "// Glyphs the title suffix needs: \" +\" then one letter per held modifier.",
        f"#define TINY18_GLYPH_SPACE {glyphs[' ']}",
        f"#define TINY18_GLYPH_PLUS {glyphs['+']}",
        f"#define TINY18_GLYPH_S {glyphs['S']}",
        f"#define TINY18_GLYPH_C {glyphs['C']}",
        f"#define TINY18_GLYPH_A {glyphs['A']}",
        f"#define TINY18_GLYPH_G {glyphs['G']}",
        "",
        "// 3x5 font, one byte per row, bit 2 is the left cell. Index 0 ends a string.",
        "static const uint8_t tiny18_glyphs[TINY18_GLYPH_COUNT][5] = {",
        "    {0x00, 0x00, 0x00, 0x00, 0x00},",
    ]
    for char, index in sorted(glyphs.items(), key=lambda item: item[1]):
        rows = ", ".join(f"0x{value:02X}" for value in glyph_rows(char))
        lines.append(f"    {{{rows}}},  // {index}: {char!r}")
    lines.extend([
        "};",
        "",
        "// Top-left corner of each key box, in the order the labels use.",
        "static const uint8_t tiny18_key_xy[TINY18_KEY_COUNT][2] = {",
        "    " + ", ".join(f"{{{x}, {y}}}" for _, x, y in cells) + ",",
        "};",
        "",
        "// \"NUMPAD\" and so on, as glyph indices, zero padded.",
        "static const uint8_t tiny18_titles[TINY18_LAYER_COUNT][TINY18_TITLE_CHARS] = {",
    ])
    for name in LAYER_TITLES:
        codes = ", ".join(str(code) for code in encode(name, glyphs, title_chars))
        lines.append(f"    {{{codes}}},")
    lines.extend([
        "};",
        "",
        "// Which label set a state shows. Index with (state & 0x1F): layer in bits",
        "// 0-2, Shift in bit 3, Ctrl in bit 4. Alt and GUI only change the title.",
        "static const uint8_t tiny18_state_set[TINY18_LABEL_STATES] = {",
        "    " + ", ".join(str(index) for index in state_set) + ",",
        "};",
        "",
        "// Per set, per key, up to two lines of glyph indices, zero padded. A zero",
        "// first glyph on the second line means the label has one line.",
        "static const uint8_t tiny18_labels[TINY18_LABEL_SETS][TINY18_KEY_COUNT][2][TINY18_LABEL_CHARS] = {",
    ])
    for set_index, labels in enumerate(sets):
        lines.append(f"    {{  // set {set_index}")
        for lines_of_key in labels:
            padded = lines_of_key + [""] * (2 - len(lines_of_key))
            parts = ", ".join("{" + ", ".join(str(code) for code in encode(line, glyphs, max_chars)) + "}" for line in padded)
            # A backslash would end the comment line with a continuation and
            # swallow the next line of the initializer.
            comment = " / ".join(line for line in lines_of_key if line).replace("\\", "BSLH")
            lines.append(f"        {{{parts}}},  // {comment}")
        lines.append("    },")
    lines.extend(["};", "", "#endif // TINY18_LAYERS_H", ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def write_preview(output: Path, layers: list, sets: list, state_set: list[int], keys: str, scale: int = 3) -> None:
    """Every layer as a row: plain, +Shift, +Ctrl, +Shift+Ctrl."""
    columns = (0, STATE_SHIFT, STATE_CTRL, STATE_SHIFT | STATE_CTRL)
    gap = 2
    sheet = Image.new("1", (WIDTH * len(columns) + gap * (len(columns) - 1), HEIGHT * 8 + gap * 7), 0)
    for layer in range(8):
        for column, mods in enumerate(columns):
            state = layer | mods
            screen = draw_state(sets[state_set[state]], layer, state, keys)
            sheet.paste(screen, (column * (WIDTH + gap), layer * (HEIGHT + gap)))
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST).save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keys", choices=sorted(LAYOUTS), default="3x3",
                        help="3x3 (default): all 18 keys as three rows of three per half; "
                             "12: the two upper rows only; 18: all keys as on the board")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="C header to write")
    parser.add_argument("--preview", type=Path, default=None, help="also write a PNG of every layer with each modifier")
    args = parser.parse_args()

    layers, _ = gen_svg.read_keymap()
    assert len(layers) == 8, f"expected eight layers, got {len(layers)}"
    sets, state_set = label_sets(layers, args.keys)
    # Drawing every state checks that each label fits its box before the
    # header is written, whether or not a preview is wanted.
    for state in range(LABEL_STATES):
        draw_state(sets[state_set[state]], state & 7, state, args.keys)
    write_header(args.out, args.keys, sets, state_set)
    print(f"wrote {args.out} ({args.keys} keys, {len(sets)} label sets for {LABEL_STATES} states)")
    if args.preview is not None:
        write_preview(args.preview, layers, sets, state_set, args.keys)
        print(f"wrote {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
