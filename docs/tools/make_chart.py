# -*- coding: utf-8 -*-
"""Draw every layer of the keymap onto one tall PNG.

Reads config/tiny18.keymap so the picture cannot drift from the firmware.
Modes come first, then the pages their thumbs open, then bluetooth. Keys are
called by what they type in text-entry mode, never by position number; the
one figure that shows numbers exists only as an index into the keymap file.
"""
import os
import re
from pathlib import Path
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from gen_svg import (read_keymap, label, held, shown, display_lines, text_names, pair,
                     PAGE_NAME, PAGE_LONG, shifted, shift_face)

# What a combo's output is for, where the key name alone does not say it.
COMBO_NOTE = {"Ctrl+Space": "日英切替"}

OUT = Path(__file__).resolve().parents[1] / "tiny18-keymap.png"


def chart_font(*, bold=False):
    """Use an installed Japanese font without distributing proprietary fonts."""
    override = os.environ.get("TINY18_FONT_BOLD" if bold else "TINY18_FONT")
    if override:
        return override
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = (
        windows_fonts / ("meiryob.ttc" if bold else "meiryo.ttc"),
        Path("/usr/share/fonts/opentype/noto") / (
            "NotoSansCJK-Bold.ttc" if bold else "NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold
             else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(
        "Install a Japanese font (e.g. fonts-noto-cjk), or set "
        "TINY18_FONT and TINY18_FONT_BOLD to font file paths."
    )

# The canvas is S times the size the layout below assumes, so the chart stays
# sharp on a high-dpi screen and through the small downscale the article
# applies. Every coordinate in this file stays in 1x units: _Draw multiplies
# them on the way into Pillow and divides measurements on the way back, so the
# layout arithmetic never has to know about S.
#
# S cannot simply be raised. Browsers cap a single image at the compositor's
# maximum texture dimension, 16384 px in Chrome and elsewhere, and quietly
# scale anything taller down before it is ever drawn - which throws away the
# very resolution S is here to add. At S = 2 this chart came out 20216 px tall
# and looked no better than before. The assert at the end of main() catches
# the day it stops fitting, so the chart fails loudly instead of quietly going
# soft again; 1.5 stopped fitting when AI mode grew two combos, and 1.4 when
# its right arrow became a third. The AI Shift face uses the remaining room at
# 1.3; the assert below guards future additions.
#
# S sets only the PNG's pixel size. The width the reader sees is fixed in
# build_html.py (SHEET_CSS_W), so lowering S costs sharpness, not size.
S = 1.3
MAX_IMAGE_PX = 16384


def _real(font):
    return font.real if isinstance(font, _Font) else font


def _scale(xy):
    """Multiply a Pillow coordinate argument, whatever shape it arrives in."""
    if isinstance(xy, (int, float)):
        return xy * S
    if isinstance(xy, (list, tuple)):
        return [_scale(value) for value in xy]
    return xy


class _Font:
    """A face rendered S times larger but measured in 1x units."""

    def __init__(self, path, size):
        self.real = ImageFont.truetype(path, int(round(size * S)))

    def getbbox(self, text, *args, **kwargs):
        return tuple(v / S for v in self.real.getbbox(text, *args, **kwargs))


class _Draw:
    """ImageDraw addressed in 1x coordinates on an S-times canvas."""

    # Pillow takes these in pixels too, so they scale with the coordinates.
    SCALED_KWARGS = ("width", "radius")

    def __init__(self, image):
        self._draw = ImageDraw.Draw(image)

    def textlength(self, text, font=None, **kwargs):
        return self._draw.textlength(text, font=_real(font), **kwargs) / S

    def __getattr__(self, name):
        method = getattr(self._draw, name)

        def call(xy, *args, **kwargs):
            kwargs = dict(kwargs)
            if kwargs.get("font") is not None:
                kwargs["font"] = _real(kwargs["font"])
            for key in self.SCALED_KWARGS:
                # Pillow wants whole pixels for these, and a non-integer S
                # would otherwise hand it a float.
                if kwargs.get(key) is not None:
                    kwargs[key] = max(1, int(round(kwargs[key] * S)))
            return method(_scale(xy), *args, **kwargs)

        return call


K, GAP = 92, 7
POS_XY = {
    0: (1, 0), 1: (2, 0), 2: (3, 0), 3: (5, 0), 4: (6, 0), 5: (7, 0),
    6: (0, 1), 7: (1, 1), 8: (2, 1), 9: (3, 1),
    10: (5, 1), 11: (6, 1), 12: (7, 1), 13: (8, 1),
    14: (1.5, 2), 15: (2.5, 2), 16: (5.5, 2), 17: (6.5, 2),
}
BLOCK_W = int(9 * (K + GAP))
KEYS_H = 3 * (K + GAP)

PALETTE = {
    "key":      ((238, 246, 255), (30, 111, 217), (18, 58, 107)),
    "mod":      ((238, 250, 243), (42, 157, 143), (23, 84, 76)),
    "shortcut": ((255, 244, 224), (184, 134, 11), (111, 81, 6)),
    "layer":    ((243, 236, 251), (122, 79, 181), (67, 42, 102)),
    "bt":       ((253, 236, 234), (192, 57, 43), (140, 35, 24)),
    "dual":     ((253, 242, 233), (211, 84, 0), (122, 48, 0)),
    "trans":    ((247, 245, 238), (201, 198, 182), (138, 134, 118)),
    "none":     ((241, 241, 234), (213, 213, 204), (154, 154, 142)),
}

# layer number -> (mode name, accent colour); same colours as the LED
MODE = {
    0: ("文字入力モード", (34, 170, 68)),
    2: ("AI モード", (30, 111, 217)),
    3: ("数字キーパッドモード", (212, 160, 23)),
    5: ("ゲームモード", (23, 184, 196)),
    4: ("ファンクションモード", (181, 56, 158)),
    1: ("Bluetooth モード", (221, 34, 34)),
}
HELD = (211, 84, 0)


@dataclass(frozen=True)
class ChartSection:
    name: str
    title: str
    subtitle: str
    colour: tuple[int, int, int]
    rule: str | None
    pressed_positions: tuple[int, ...] = ()


@dataclass(frozen=True)
class ChartModel:
    bindings: dict[str, list[str]]
    layer_names: list[str]
    key_names: list[str]
    entry: dict[int, str]
    holders: dict[int, list[str]]
    sections: tuple[ChartSection, ...]


@dataclass(frozen=True)
class ComboCard:
    name: str
    positions: tuple[int, ...]
    output: str
    note: str


@dataclass(frozen=True)
class ComboCardGroup:
    heading: str
    colour: tuple[int, int, int]
    cards: tuple[ComboCard, ...]


def chart_model(layers, combos):
    """Build the user-visible chart order and its derived Shift faces."""
    bindings = dict(layers)
    bindings["nav_shift"] = [shifted(tok) for tok in bindings["nav_layer"]]
    bindings["digit_symbol_shift"] = shift_face(bindings["digit_symbol_layer"])
    bindings["edit_bracket_shift"] = shift_face(bindings["edit_bracket_layer"])
    bindings["number_shift"] = [shifted(tok) for tok in bindings["number_layer"]]
    bindings["game_shift"] = [shifted(tok) for tok in bindings["game_layer"]]
    layer_names = [name for name, _ in layers]
    key_names = text_names(layers)

    entry = {}
    for combo in combos:
        if combo["name"].startswith("mode_"):
            target = int(combo["binding"].replace("&to ", ""))
            entry[target] = pair(combo["pos"], key_names)

    holders = {}
    holder_positions = {}
    for position, tok in enumerate(bindings["default_layer"]):
        match = re.match(r"&b?lt (\d+)", tok)
        if match:
            layer = int(match.group(1))
            holders.setdefault(layer, []).append(key_names[position])
            holder_positions.setdefault(layer, []).append(position)

    def shift_positions(layer):
        return tuple(
            position
            for position, tok in enumerate(bindings[layer_names[layer]])
            if held(tok) == "Shift"
        )

    def held_page_subtitle(layer, *, with_shift=False):
        names = " か ".join(holders[layer])
        if with_shift:
            page = bindings[layer_names[layer]]
            shifts = " か ".join(
                key_names[position]
                for position, tok in enumerate(page)
                if held(tok) == "Shift"
            )
            names = f"{names} と {shifts}"
        return f"{names} を押さえている間"

    nav_shifts = " か ".join(
        key_names[position]
        for position, tok in enumerate(bindings["nav_layer"])
        if held(tok) == "Shift"
    )
    game_shifts = " か ".join(
        key_names[position]
        for position, tok in enumerate(bindings["game_layer"])
        if held(tok) == "Shift"
    )

    sections = (
        ChartSection("nav_layer", "AI モード", f"{entry[2]} で入る", MODE[2][1], None),
        ChartSection("nav_shift", "AI モード（Shift）",
                     f"{nav_shifts} を押さえている間", MODE[2][1], None),
        ChartSection("default_layer", "文字入力モード",
                     f"{entry[0]} で入る", MODE[0][1], "ここから下は文字と記号"),
        ChartSection("digit_symbol_layer", PAGE_NAME[6],
                     held_page_subtitle(6), HELD, None,
                     tuple(holder_positions[6])),
        ChartSection("digit_symbol_shift", PAGE_NAME[6] + "（Shift）",
                     held_page_subtitle(6, with_shift=True), HELD, None,
                     tuple(holder_positions[6]) + shift_positions(6)),
        ChartSection("edit_bracket_layer", PAGE_NAME[7],
                     held_page_subtitle(7), HELD, None,
                     tuple(holder_positions[7])),
        ChartSection("edit_bracket_shift", PAGE_NAME[7] + "（Shift）",
                     held_page_subtitle(7, with_shift=True), HELD, None,
                     tuple(holder_positions[7]) + shift_positions(7)),
        ChartSection("number_layer", "数字キーパッドモード",
                     f"{entry[3]} で入る", MODE[3][1], "ここから下は、切り替えて入るモード"),
        ChartSection("number_shift", "数字キーパッドモード（Shift）",
                     f"{key_names[13]} を押さえている間", MODE[3][1], None),
        ChartSection("fn_layer", "ファンクションモード",
                     f"{entry[4]} で入る", MODE[4][1], None),
        ChartSection("game_layer", "ゲームモード",
                     f"{entry[5]} で入る", MODE[5][1], None),
        ChartSection("game_shift", "ゲームモード（Shift）",
                     f"{game_shifts} を押さえている間", MODE[5][1], None),
        ChartSection("bluetooth_layer", "Bluetooth モード",
                     f"{entry[1]} で入る", MODE[1][1], None),
    )
    return ChartModel(bindings, layer_names, key_names, entry, holders, sections)


def combo_card_groups(model, combos):
    """Build the complete combo-card list without a duplicate text table."""
    by_name = {combo["name"]: combo for combo in combos}

    def target(combo):
        layer = int(combo["binding"].replace("&to ", ""))
        return MODE[layer][0]

    def scope_name(layer):
        if layer in PAGE_NAME:
            return PAGE_NAME[layer] + "の面"
        return MODE[layer][0]

    def where(combo):
        layer = combo["layers"][0]
        keys = " と ".join(
            label(model.bindings[model.layer_names[layer]][position])[0].split("\n")[0]
            for position in combo["pos"]
        )
        if layer in model.holders:
            held_by = " か ".join(model.holders[layer])
            return f"{held_by}を押さえる。{scope_name(layer)}では {keys}"
        return f"{scope_name(layer)}では {keys}"

    def notes(*parts):
        return "／".join(part for part in parts if part)

    def idle_note(combo):
        return f"打鍵後 {combo['idle']}ms" if combo["idle"] else ""

    switch = []
    text = []
    ai = []
    held_or_number = []
    for combo in combos:
        if combo["name"].startswith("mode_"):
            switch.append(ComboCard(
                combo["name"], tuple(combo["pos"]), target(combo),
                notes(idle_note(combo), "ゲームモードでは無効" if 5 not in combo["layers"] else ""),
            ))
            continue

        output = label(combo["binding"])[0]
        if 0 in combo["layers"]:
            other_scopes = [scope_name(layer) for layer in combo["layers"] if layer != 0]
            text.append(ComboCard(
                combo["name"], tuple(combo["pos"]), output,
                notes(COMBO_NOTE.get(output, ""),
                      "・".join(other_scopes) + "でも同じ" if other_scopes else "",
                      idle_note(combo)),
            ))
        elif combo["layers"] == [2]:
            ai.append(ComboCard(
                combo["name"], tuple(combo["pos"]), output,
                notes(where(combo), idle_note(combo)),
            ))
        else:
            held_or_number.append(ComboCard(
                combo["name"], tuple(combo["pos"]), output,
                notes(where(combo), idle_note(combo)),
            ))

    assert set(by_name) == {
        card.name for cards in (switch, text, ai, held_or_number) for card in cards
    }
    return (
        ComboCardGroup("モード切替", (26, 58, 92), tuple(switch)),
        ComboCardGroup("文字入力モード", (34, 170, 68), tuple(text)),
        ComboCardGroup("AI モード", MODE[2][1], tuple(ai)),
        ComboCardGroup("そのモードや面の中だけ", HELD, tuple(held_or_number)),
    )


def shorten(t):
    return {"Space": "Spc", "Enter": "Ent", "Shift": "Sft", "R Shift": "RSft",
            "R Ctrl": "RCtl", "R Alt": "RAlt", "BackSpace": "BkSp",
            "\\": "＼"}.get(t, t)


MK, MG = 32, 4          # small key size and gap for the combo thumbnails
MINI_STEP = MK + MG
MINI_W = 9 * MINI_STEP - MG
MINI_H = 3 * MINI_STEP - MG


def mini(d, ox, oy, pressed, colour):
    """Draw the 18-key map small, with the combo's own keys filled in."""
    for i in range(18):
        cx, cy = POS_XY[i]
        x, y = ox + cx * MINI_STEP, oy + cy * MINI_STEP
        if i in pressed:
            d.rounded_rectangle([x, y, x + MK, y + MK], radius=4,
                                fill=colour, outline=colour, width=2)
        else:
            d.rounded_rectangle([x, y, x + MK, y + MK], radius=4,
                                fill=(240, 240, 236), outline=(216, 216, 210), width=1)
    mx = ox + 4.35 * MINI_STEP
    d.line([(mx, oy - 3), (mx, oy + MINI_H + 3)], fill=(203, 203, 203), width=2)


def main():
    layers, combos = read_keymap()
    model = chart_model(layers, combos)
    B = model.bindings
    NAMES = model.key_names
    entry = model.entry
    SECTIONS = model.sections

    FONT, BOLD = chart_font(), chart_font(bold=True)
    f_h1 = _Font(BOLD, 46)
    f_meta = _Font(FONT, 22)
    f_sec = _Font(BOLD, 30)
    f_sub = _Font(FONT, 21)
    f_key = _Font(BOLD, 36)
    f_med = _Font(BOLD, 23)
    f_sml = _Font(BOLD, 17)
    f_tiny = _Font(BOLD, 13)
    f_body = _Font(FONT, 22)
    f_mono = _Font(BOLD, 22)
    f_out = _Font(BOLD, 28)
    f_num = _Font(FONT, 16)

    MARGIN = 56
    W = MARGIN * 2 + BLOCK_W
    head_h, sec_h, gap_h = 190, 46, 40
    intro_h = 420
    # The canvas only has to be at least as tall as the drawing; it is cropped
    # to the real height below, so slack here costs nothing but memory. Running
    # short is what costs: Pillow pads a crop past the edge with black, so the
    # bottom of the chart goes missing behind a black band. The assert after
    # the drawing is what turns that into a failure instead of a silent one.
    combo_h = 6200
    H = head_h + intro_h + len(SECTIONS) * (sec_h + KEYS_H + gap_h) + combo_h + MARGIN + 2000

    img = Image.new("RGB", (int(W * S), int(H * S)), (250, 250, 247))
    d = _Draw(img)

    d.text((MARGIN, 44), "Tiny18 キーマップ", font=f_h1, fill=(26, 58, 92))
    d.text((MARGIN, 104), "18 キーを 6 つのモードで使い分ける   "
                          "図は config/tiny18.keymap から生成",
           font=f_meta, fill=(110, 110, 110))
    d.line([(MARGIN, head_h - 24), (W - MARGIN, head_h - 24)], fill=(26, 58, 92), width=4)

    # ---- intro: the four modes --------------------------------------------
    y = head_h
    d.text((MARGIN, y), "まず 4 つのモードがある", font=f_sec, fill=(26, 58, 92))
    y += 48
    for n, layer in enumerate([2, 0, 3, 5]):
        nm, col = MODE[layer]
        bw = (BLOCK_W - 20) // 2
        x = MARGIN + (n % 2) * (bw + 20)
        by = y + (n // 2) * 106
        d.rounded_rectangle([x, by, x + bw, by + 92], radius=10,
                            fill=(255, 255, 255), outline=col, width=4)
        d.text((x + 24, by + 14), "%d. %s" % (n + 1, nm), font=f_sec, fill=col)
        d.text((x + 24, by + 54), entry[layer] + " で入る", font=f_body, fill=(90, 90, 90))
    y += 228
    for line in ["ファンクションモードと Bluetooth モードも、同じように 2 キーで入れる。",
                 "親指を押さえている間だけ開く面が 2 つある。%s、%s。"
                 % (PAGE_LONG[6], PAGE_LONG[7]),
                 "図中の英字は、入力結果の大小ではなくキー名として大文字で表す。"]:
        d.text((MARGIN, y), line, font=f_body, fill=(90, 90, 90))
        y += 32

    # ---- each layer --------------------------------------------------------
    def draw_keys(top, bindings, letter_case=None):
        mid = MARGIN + 4.35 * (K + GAP)
        d.line([(mid, top - 4), (mid, top + KEYS_H)], fill=(205, 205, 205), width=3)
        for i in range(18):
            cx, cy = POS_XY[i]
            x = MARGIN + cx * (K + GAP)
            ky = top + cy * (K + GAP)
            text, cat = shown(bindings[i], B["default_layer"], i, letter_case=letter_case)
            fill, stroke, tcol = PALETTE[cat]
            d.rounded_rectangle([x, ky, x + K, ky + K], radius=10, fill=fill,
                                outline=stroke,
                                width=3 if cat not in ("trans", "none") else 2)
            lines = [shorten(l) for l in display_lines(text)]
            longest = max(len(l) for l in lines)
            candidates = ((f_key, f_med, f_sml, f_tiny)
                          if len(lines) == 1 and longest <= 3
                          else (f_med, f_sml, f_tiny))
            f = next((candidate for candidate in candidates
                      if all(d.textlength(line, font=candidate) <= K - 8 for line in lines)), f_tiny)
            assert all(d.textlength(line, font=f) <= K - 8 for line in lines), (i, lines)
            # Every line takes the height of a reference pair of glyphs, so a
            # line that is only a comma or a full stop keeps a row of its own
            # and sits on its baseline instead of collapsing onto the line
            # below, as it did when each line was measured by itself.
            ref = f.getbbox("Ag")
            lh = ref[3] - ref[1] + 4
            yy = ky + (K - lh * len(lines)) / 2
            for l in lines:
                d.text((x + (K - d.textlength(l, font=f)) / 2, yy - ref[1]), l,
                       font=f, fill=tcol)
                yy += lh

    y = head_h + intro_h
    for section in SECTIONS:
        name, title, sub, col, rule = (
            section.name, section.title, section.subtitle,
            section.colour, section.rule,
        )
        if rule is not None:
            # Everything above the first rule is one hand on the home position;
            # below are the modes you switch into and come back from.
            d.line([(MARGIN, y + 4), (W - MARGIN, y + 4)], fill=(26, 58, 92), width=3)
            if rule:
                d.text((MARGIN, y + 18), rule, font=f_body, fill=(110, 110, 110))
                y += 66
            else:
                y += 30
        d.rectangle([MARGIN, y, MARGIN + 10, y + 34], fill=col)
        d.text((MARGIN + 24, y - 2), title, font=f_sec, fill=(26, 58, 92))
        tw = d.textlength(title, font=f_sec)
        d.text((MARGIN + 24 + tw + 20, y + 8), sub, font=f_sub, fill=(120, 120, 120))
        head = sec_h
        if section.pressed_positions:
            # Show every alternative held position. The subtitle distinguishes
            # alternatives ("か") from keys that must be held together ("と").
            mini(d, MARGIN + 24, y + 44, set(section.pressed_positions), col)
            held_label = sub.removesuffix(" を押さえている間")
            d.text((MARGIN + 24 + MINI_W + 30, y + 58),
                   held_label + " を", font=f_med, fill=col)
            d.text((MARGIN + 24 + MINI_W + 30, y + 96),
                   "押さえている間", font=f_body, fill=(90, 90, 90))
            head = sec_h + MINI_H + 36
        top = y + head
        draw_keys(top, B[name])
        y = top + KEYS_H + gap_h

    # ---- key names and position numbers ------------------------------------
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=(26, 58, 92), width=3)
    y += 26
    d.text((MARGIN, y), "キーの名前と position 番号", font=f_sec, fill=(26, 58, 92))
    d.text((MARGIN + 420, y + 8), "番号は keymap ファイルを読むときの索引",
           font=f_sub, fill=(120, 120, 120))
    top = y + sec_h
    mid = MARGIN + 4.35 * (K + GAP)
    d.line([(mid, top - 4), (mid, top + KEYS_H)], fill=(205, 205, 205), width=3)
    for i in range(18):
        cx, cy = POS_XY[i]
        x = MARGIN + cx * (K + GAP)
        ky = top + cy * (K + GAP)
        d.rounded_rectangle([x, ky, x + K, ky + K], radius=10,
                            fill=(246, 248, 250), outline=(184, 194, 204), width=2)
        nm = shorten(NAMES[i])
        f = f_key if len(nm) <= 3 else f_med
        d.text((x + (K - d.textlength(nm, font=f)) / 2, ky + 14), nm, font=f, fill=(36, 41, 46))
        d.text((x + K - 10 - d.textlength(str(i), font=f_num), ky + K - 26), str(i),
               font=f_num, fill=(140, 140, 140))
    yy = top + KEYS_H + 24
    left = [0, 1, 2, 6, 7, 8, 9, 14, 15]
    right = [3, 4, 5, 10, 11, 12, 13, 16, 17]
    for line in ["左手 = " + " ".join(NAMES[p] for p in left),
                 "右手 = " + " ".join(NAMES[p] for p in right)]:
        d.text((MARGIN + 12, yy), line, font=f_mono, fill=(60, 60, 60))
        yy += 30

    # ---- combos, drawn once on the key map ---------------------------------
    yy += 40
    d.line([(MARGIN, yy), (W - MARGIN, yy)], fill=(26, 58, 92), width=3)
    yy += 26
    d.text((MARGIN, yy), "combo で押す位置", font=f_sec, fill=(26, 58, 92))
    yy += 52

    CARD_H = MINI_H + 26
    TX = MARGIN + MINI_W + 44          # where the label column starts

    def cards(group):
        """One combo per row: the key map on the left, what it does on the right."""
        nonlocal yy
        d.text((MARGIN, yy), group.heading, font=f_body, fill=(90, 90, 90))
        yy += 40
        for card in group.cards:
            mini(d, MARGIN, yy, set(card.positions), group.colour)
            ty = yy + (22 if card.note else 34)
            ks = pair(card.positions, NAMES, "+")
            d.text((TX, ty), ks, font=f_sec, fill=(26, 58, 92))
            d.text((TX + d.textlength(ks, font=f_sec) + 26, ty), card.output,
                   font=f_out, fill=(45, 45, 45))
            if card.note:
                d.text((TX, ty + 44), card.note, font=f_sub, fill=(140, 140, 140))
            yy += CARD_H
        yy += 24

    for group in combo_card_groups(model, combos):
        cards(group)

    assert int(yy) + MARGIN <= H, (
        "drawing ran %d px past the canvas; raise H. Cropping past the edge "
        "pads with black and loses the bottom." % (int(yy) + MARGIN - H))
    img = img.crop((0, 0, int(W * S), int((int(yy) + MARGIN) * S)))
    assert img.height <= MAX_IMAGE_PX, (
        "chart is %d px tall; browsers cap a single image at %d and scale the "
        "rest away. Lower S or split the output." % (img.height, MAX_IMAGE_PX))
    img.save(OUT)
    print("wrote", OUT, img.size, "headroom", MAX_IMAGE_PX - img.height, "px")


if __name__ == "__main__":
    main()
