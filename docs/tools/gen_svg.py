# -*- coding: utf-8 -*-
"""Render each keymap layer as an SVG in the style the existing note uses.

Reads the firmware keymap so the published diagrams cannot drift from what is
actually flashed. Emits a fragment per layer plus the combo table.
"""
import io, re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEYMAP = ROOT / "config" / "tiny18.keymap"

# Rect origin per position; label sits at (x+24, y+29). Same numbers as the
# existing figure 1, so every diagram lines up with it.
POS = {
    0: (60, 30), 1: (112, 30), 2: (164, 30),
    3: (372, 30), 4: (424, 30), 5: (476, 30),
    6: (8, 108), 7: (60, 82), 8: (112, 82), 9: (164, 82),
    10: (372, 82), 11: (424, 82), 12: (476, 82), 13: (528, 108),
    14: (138, 134), 15: (190, 134),
    16: (294, 134), 17: (346, 134),
}

DIM = ("#f1f1ea", "#d5d5cc", "#9a9a8e", 1)  # fill, stroke, text, stroke-width

# Held layers are named after what they hold, never by number. Short enough to
# fit inside a key box; prose adds "の面" around these.
PAGE_NAME = {6: "数字", 7: "ZXCV"}
PAGE_LONG = {6: "数字の面", 7: "ZXCV の面"}

# Only these text-entry faces describe letter case rather than key names.
LETTER_CASE_LAYERS = frozenset(("default_layer", "edit_bracket_layer"))

# Keys a macro sends that put no character on the host: LANG2 only sets the
# IME to alphanumeric. Left out of the macro's label.
SILENT_KEYS = {"LANG1", "LANG2"}

# Prose calls a key by what it types in text-entry mode, so these expand the
# short key-cap labels back out.
LONG = {"BkSp": "BackSpace"}


def text_names(layers):
    """Text-mode tap label per position: the name prose uses for that key."""
    base = dict(layers)["default_layer"]
    out = []
    for tok in base:
        tap = label(tok)[0].split("\n")[0]
        out.append(LONG.get(tap, tap))
    return out


def pair(positions, names, sep=" + "):
    return sep.join(names[p] for p in positions)


MACRO_TEXT = {}          # macro label -> the text it types, filled by read_keymap
MACRO_HOLD = {}          # hold-tap name -> the macro its hold side runs, if any
KP_HOLD_TAP = set()      # hold-tap names whose two sides are both &kp
MORPH = {}               # mod-morph name -> (plain binding, binding while Shift is held)


def read_macros(s):
    """What each macro actually sends, read from its own bindings so a key box
    cannot claim something the firmware does not type."""
    MACRO_TEXT.clear()
    block = re.search(r"\n    macros \{(.*?)\n    \};", s, re.S)
    if not block:
        return
    for name, body in re.findall(r"(\w+): \w+ \{(.*?)\};", block.group(1), re.S):
        bindings = re.search(r"bindings = (.*?);", body, re.S)
        if not bindings:
            continue
        out = []
        mode = "tap"
        for item in re.findall(r"&macro_(?:press|release|tap)|&kp \w+", bindings.group(1)):
            if item.startswith("&macro_"):
                mode = item.removeprefix("&macro_")
                continue
            if mode != "tap":
                continue
            key = item.removeprefix("&kp ")
            if key in SILENT_KEYS:
                continue
            text = label("&kp " + key)[0]
            if key == "ENTER":
                out.append("⏎")
            else:
                # Letters are named in upper case but typed in lower without
                # a Shift, so the label has to follow what arrives.
                out.append(text.lower() if len(text) == 1 and text.isalpha() else text)
        text = "".join(out)
        # A trailing Enter goes on its own line: the key box picks its font
        # from the longest line, and one extra glyph would shrink the whole
        # command to fit beside it.
        MACRO_TEXT[name] = text[:-1] + "\n⏎" if text.endswith("⏎") else text


def read_behaviors(s):
    """What the keymap's own behaviors do, read from the behaviors block so a
    key box never keeps its own copy of the answer.

    Two kinds matter here: hold-taps whose hold side runs a macro, and
    mod-morphs, which send one binding normally and another while Shift is
    held."""
    MACRO_HOLD.clear()
    KP_HOLD_TAP.clear()
    MORPH.clear()
    block = re.search(r"\n    behaviors \{(.*?)\n    \};", s, re.S)
    if not block:
        return
    for name, body in re.findall(r"(\w+): \w+ \{(.*?)\};", block.group(1), re.S):
        bindings = re.search(r"bindings = (.*?);", body, re.S)
        if not bindings:
            continue
        if "behavior-mod-morph" in body:
            pair = re.findall(r"<\s*(&[^>]+?)\s*>", bindings.group(1))
            if len(pair) == 2:
                MORPH[name] = (pair[0], pair[1])
            continue
        held_side = re.findall(r"<\s*&(\w+)\s*>", bindings.group(1))
        if held_side and held_side[0] in MACRO_TEXT:
            MACRO_HOLD[name] = held_side[0]
        if "behavior-hold-tap" in body and held_side == ["kp", "kp"]:
            KP_HOLD_TAP.add(name)


def shifted(tok):
    """What a key sends while Shift is held, for the keys that change."""
    return MORPH[tok[1:]][1] if tok[1:] in MORPH else tok


# What an ordinary keyboard key produces while Shift is held. Mod-morph
# bindings are resolved first by ``shifted``; this table covers keys whose
# shifted result is produced by the host keyboard layout instead.
HOST_SHIFT_OUTPUT = {
    "N1": "!", "N2": "@", "N3": "#", "N4": "$", "N5": "%", "N6": "^",
    "N7": "&", "N8": "*", "N9": "(", "N0": ")", "MINUS": "_", "EQUAL": "+",
    "GRAVE": "~", "LEFT_BRACKET": "{", "RIGHT_BRACKET": "}",
    "BACKSLASH": "|", "SEMICOLON": ":", "SINGLE_QUOTE": '"',
    "SLASH": "?", "COMMA": "<", "PERIOD": ">",
}


def shift_face(bindings):
    """Bindings as shown while Shift is held.

    The result is documentation data, not a replacement keymap: ordinary
    punctuation is written as the character the host receives, while custom
    mod-morph behaviors are resolved from the keymap itself.
    """
    out = []
    for tok in bindings:
        tok = shifted(tok)
        match = re.fullmatch(r"&kp (\w+)", tok)
        if match and match.group(1) in HOST_SHIFT_OUTPUT:
            tok = "&kp " + HOST_SHIFT_OUTPUT[match.group(1)]
        out.append(tok)
    return out


SHIFTED_SYMBOL = {"1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^",
                  "7": "&", "8": "*", "9": "(", "0": ")", "-": "_", "=": "+",
                  ",": "<", ".": ">", "/": "?"}


def shifted_symbol(tok):
    """The symbol a held page produces with Shift, including mod-morphs."""
    morphed = shifted(tok)
    if morphed != tok:
        return label(morphed)[0]
    return SHIFTED_SYMBOL.get(label(tok)[0])


def read_keymap():
    with io.open(KEYMAP, encoding="utf-8") as fh:
        s = fh.read()
    read_macros(s)
    read_behaviors(s)
    km = s[s.index("keymap {"):]
    layers = []
    for name, body in re.findall(r"(\w+) \{\s*\n\s*bindings = <\n(.*?)\n\s*>;", km, re.S):
        toks = re.findall(r"&\w+(?:\s+[A-Z0-9_()]+)*", body)
        assert len(toks) == 18, (name, len(toks))
        layers.append((name, [t.strip() for t in toks]))
    combos = []
    cs = s[s.index("combos {"):s.index("keymap {")]
    for name, body in re.findall(r"(\w+) \{\s*\n((?:\s*[\w-]+ = <[^>]*>;\s*\n)+)\s*\};", cs):
        combos.append({
            "name": name,
            "binding": re.search(r"bindings = <([^>]*)>", body).group(1).strip(),
            "pos": [int(x) for x in re.search(r"key-positions = <([^>]*)>", body).group(1).split()],
            "layers": [int(x) for x in re.search(r"layers = <([^>]*)>", body).group(1).split()],
            "idle": (re.search(r"require-prior-idle-ms = <(\d+)>", body) or [None, None])[1]
                     if re.search(r"require-prior-idle-ms = <(\d+)>", body) else None,
        })
    return layers, combos


def label(tok):
    """Short human label for a binding, plus a category used for colouring."""
    if tok in ("&trans",):
        return "\u2014", "trans"
    if tok in ("&none",):
        return "\u2014", "none"
    m = re.match(r"&kp (.+)", tok)
    if m:
        k = m.group(1)
        table = [
            ("LEFT_CONTROL", "Ctrl"), ("LCTRL", "Ctrl"), ("RCTRL", "R Ctrl"),
            ("LEFT_ARROW", "\u2190"), ("RIGHT_ARROW", "\u2192"),
            ("UP_ARROW", "\u2191"), ("DOWN_ARROW", "\u2193"),
            ("BACKSPACE", "BkSp"), ("ESCAPE", "Esc"), ("PRINTSCREEN", "PrtSc"),
            ("DOUBLE_QUOTES", "\""), ("COLON", ":"), ("SLASH", "/"),
            ("COMMA", ","), ("PERIOD", "."),
            ("LSHFT", "Shift"), ("RIGHT_SHIFT", "R Shift"),
            ("LEFT_ALT", "Alt"), ("LALT", "Alt"), ("RALT", "R Alt"),
            ("LEFT_GUI", "GUI"), ("PAGE_UP", "PgUp"), ("PAGE_DOWN", "PgDn"),
            ("HOME", "Home"), ("END", "End"), ("INSERT", "Ins"),
            ("CAPS", "CapsLk"), ("CAPSLOCK", "CapsLk"), ("SCROLLLOCK", "ScrLk"),
            ("PAUSE_BREAK", "Pause"), ("K_APP", "Menu"), ("K_APPLICATION", "Menu"),
            ("KP_SLASH", "/"), ("KP_ASTERISK", "*"), ("KP_DIVIDE", "/"),
            ("KP_MULTIPLY", "*"),
            ("SPACE", "Space"), ("ENTER", "Enter"),
            ("MINUS", "-"), ("PLUS", "+"), ("HASH", "#"), ("TILDE", "~"),
            ("SEMICOLON", ";"), ("SINGLE_QUOTE", "'"), ("GRAVE", "`"),
            ("AMPERSAND", "&"), ("ASTERISK", "*"), ("CARET", "^"),
            ("LEFT_PARENTHESIS", "("), ("RIGHT_PARENTHESIS", ")"),
            ("DOLLAR", "$"), ("PERCENT", "%"),
            ("EXCLAMATION", "!"), ("AT_SIGN", "@"),
            ("LEFT_BRACKET", "["), ("RIGHT_BRACKET", "]"),
            ("BACKSLASH", "\\"), ("TAB", "Tab"), ("DELETE", "Del"), ("EQUAL", "="),
            ("QUESTION", "?"), ("QMARK", "?"), ("EXCL", "!"),
            ("KP_NUMLOCK", "NumLk"), ("KP_DOT", "."), ("KP_MINUS", "-"),
            ("KP_PLUS", "+"), ("KP_EQUAL", "="), ("KP_ENTER", "Enter"),
        ]
        for a, b in table:
            if k == a:
                k = b
                break
        # Keypad digits print as the digit they send; the caption says the mode
        # uses keypad usages, which is not something a key box can show.
        k = re.sub(r"^KP_N(\d)$", r"\1", k)
        k = re.sub(r"^N(\d)$", r"\1", k)
        modifiers = []
        modifier_names = {"LC": "Ctrl", "LS": "Shift", "LA": "Alt", "LG": "GUI",
                          "RC": "R Ctrl", "RS": "R Shift", "RA": "R Alt", "RG": "R GUI"}
        while True:
            modified = re.fullmatch(r"([LR][CSAG])\((.*)\)", k)
            if not modified:
                break
            modifiers.append(modifier_names[modified.group(1)])
            k = modified.group(2)
        if modifiers:
            k = {"SPACE": "Space"}.get(k, k)
            return "+".join(modifiers + [k]), "shortcut"
        cat = "mod" if k in ("Shift", "Ctrl", "Alt", "R Ctrl", "R Alt", "GUI",
                             "Space", "Enter", "R Shift") else "key"
        return k, cat
    m = re.match(r"&mo (\d+)", tok)
    if m:
        # A page with no tap of its own: name the page, not the layer number.
        return PAGE_NAME.get(int(m.group(1)), m.group(1)) + "\nを開く", "layer"
    m = re.match(r"&to (\d+)", tok)
    if m:
        return "\u21d2 " + m.group(1), "layer"
    m = re.match(r"&b?lt (\d+) (.+)", tok)
    if m:
        # Tap on top, the page it opens underneath, by name rather than number.
        page = PAGE_NAME.get(int(m.group(1)), "hold " + m.group(1))
        return label("&kp " + m.group(2))[0] + "\n" + page, "dual"
    # A hold-tap whose hold runs a macro: tap on top, what the macro types
    # underneath. The first parameter is the unused one a macro cannot take.
    m = re.match(r"&(\w+) \S+ (.+)", tok)
    if m and m.group(1) in MACRO_HOLD:
        return (label("&kp " + m.group(2))[0] + "\n"
                + MACRO_TEXT[MACRO_HOLD[m.group(1)]]), "dual"
    m = re.match(r"&(\w+) (\w+) (.+)", tok)
    if m and m.group(1) in KP_HOLD_TAP:
        return (label("&kp " + m.group(3))[0] + "\n"
                + label("&kp " + m.group(2))[0]), "dual"
    m = re.match(r"&bt BT_SEL (\d+)", tok)
    if m:
        return "BT " + m.group(1), "bt"
    if tok[1:] in MORPH:
        # A key box shows what the key does now; the Shift face has its own
        # figure and the display draws it under "+S".
        return label(MORPH[tok[1:]][0])
    if tok[1:] in MACRO_TEXT:
        return MACRO_TEXT[tok[1:]], "shortcut"
    return tok.replace("&", ""), "key"


def held(tok):
    """What a key does while held: the modifier of a mod-tap, the page a
    layer-tap or &mo opens, or the key itself when it is plain. The symbol
    tables use it to find Shift whether it is bare or the hold of Enter."""
    m = re.match(r"&(\w+) \S+ ", tok)
    if m and m.group(1) in MACRO_HOLD:
        return MACRO_TEXT[MACRO_HOLD[m.group(1)]]
    m = re.match(r"&(\w+) (\w+) ", tok)
    if m and m.group(1) in KP_HOLD_TAP:
        return label("&kp " + m.group(2))[0]
    m = re.match(r"&b?lt (\d+) ", tok) or re.match(r"&mo (\d+)$", tok)
    if m:
        return PAGE_NAME.get(int(m.group(1)), m.group(1))
    return label(tok)[0].split("\n")[0]


def format_letter_label(text, case):
    """Format a one-letter tap; preserve hold names and shortcut labels."""
    if case not in ("lower", "upper", "pair"):
        raise ValueError(f"unknown letter case: {case}")
    lines = text.split("\n")
    if re.fullmatch(r"[A-Za-z]", lines[0]):
        letter = lines[0]
        lines[0] = (letter.lower() if case == "lower" else letter.upper()
                    if case == "upper" else letter.lower() + "/" + letter.upper())
    return "\n".join(lines)


def shown(tok, base, i, *, letter_case=None):
    """Label and category of a binding as the reader should see it. A &trans
    key keeps the dimmed transparent style but shows what it falls through
    to, the text-entry binding at that position: every transparent key in
    this keymap ends up there, whether directly or through AI mode."""
    text, cat = label(tok)
    if cat == "trans" and base is not None:
        text = label(base[i])[0]
    if letter_case is not None:
        text = format_letter_label(text, letter_case)
    return text, cat


def display_lines(text):
    """Split long slash commands only when drawing a key box."""
    if text.startswith("Ctrl+Shift+"):
        return ["Ctrl+", text[len("Ctrl+"):]]
    if "\n" not in text and text.startswith("/") and len(text) > 8:
        middle = (len(text) + 1) // 2
        return [text[:middle], text[middle:]]
    return text.split("\n")


PALETTE = {
    "key":      ("#eef6ff", "#1e6fd9", "#123a6b", 2),
    "mod":      ("#eefaf3", "#2a9d8f", "#17544c", 2),
    "shortcut": ("#fff4e0", "#b8860b", "#6f5106", 2),
    "layer":    ("#f3ecfb", "#7a4fb5", "#432a66", 2),
    "bt":       ("#fdecea", "#c0392b", "#8c2318", 2),
    "dual":     ("#fdf2e9", "#d35400", "#7a3000", 2),
    "trans":    ("#f7f5ee", "#c9c6b6", "#8a8676", 1),
    "none":     DIM,
}


def svg(bindings, aria, accent=None, base=None, *, letter_case=None):
    out = ['<svg viewBox="0 0 584 190" role="img" aria-label="%s">' % aria,
           '<text x="123" y="20" text-anchor="middle" font-size="13" fill="#5a6a72" font-family="sans-serif">\u5de6\u624b\u5074</text>',
           '<text x="435" y="20" text-anchor="middle" font-size="13" fill="#5a6a72" font-family="sans-serif">\u53f3\u624b\u5074</text>',
           '<line x1="266" y1="8" x2="266" y2="184" stroke="#ccc" stroke-dasharray="5 5" stroke-width="1.5"/>']
    for i in range(18):
        x, y = POS[i]
        text, cat = shown(bindings[i], base, i, letter_case=letter_case)
        fill, stroke, tcol, sw = PALETTE[cat]
        if accent and cat not in ("trans", "none"):
            fill, stroke, tcol, sw = accent
        out.append('<rect x="%d" y="%d" width="48" height="48" rx="6" fill="%s" stroke="%s" stroke-width="%d"/>'
                   % (x, y, fill, stroke, sw))
        lines = display_lines(text)
        size = 15.0 if (len(lines) == 1 and len(lines[0]) <= 2) else (
            11.0 if max(len(l) for l in lines) <= 6 else (
                9.0 if max(len(l) for l in lines) <= 8 else 6.0))
        if len(lines) == 1:
            out.append('<text x="%d" y="%d" text-anchor="middle" font-size="%.1f" font-weight="bold" fill="%s" font-family="sans-serif">%s</text>'
                       % (x + 24, y + 29, size, tcol, esc(lines[0])))
        else:
            for n, l in enumerate(lines):
                out.append('<text x="%d" y="%d" text-anchor="middle" font-size="%.1f" font-weight="bold" fill="%s" font-family="sans-serif">%s</text>'
                           % (x + 24, y + 23 + n * 13, size, tcol, esc(l)))
    out.append('</svg>')
    return "\n".join(out)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# What the page's table and the chart both list as reachable with two fingers.
TWO_KEY_WANTS = [",", "."]


def hold_pages(layers):
    """Base-layer positions that open a page while held, mapped to that page."""
    pages = {}
    for p, tok in enumerate(dict(layers)["default_layer"]):
        m = re.match(r"&b?lt (\d+) ", tok) or re.match(r"&mo (\d+)$", tok)
        if m:
            pages[p] = int(m.group(1))
    return pages


def two_key_routes(layers, want):
    """Every two-finger route to `want`: one key held to open a page, one key
    tapped on it, keyed by the tapped key's name. Both the page and the chart
    read this, so neither can keep a route the keymap no longer has.

    A held modifier plus a base-layer tap is left out on purpose. Ctrl on M
    with Space fails two ways, which is why Ctrl+Space has a key of its own."""
    names = text_names(layers)
    order = [n for n, _ in layers]
    by_name = dict(layers)
    routes = {}
    for h, lay in hold_pages(layers).items():
        for p, tok in enumerate(by_name[order[lay]]):
            # The held key is busy holding, so it cannot also be the tap.
            if p != h and label(tok)[0] == want:
                routes.setdefault(names[p], []).append(names[h])
    return routes


if __name__ == "__main__":
    layers, combos = read_keymap()
    result = {"layers": [], "combos": combos}
    for name, b in layers:
        result["layers"].append({"name": name, "svg": svg(b, name), "bindings": b})
    io.open(sys.argv[1], "w", encoding="utf-8").write(
        json.dumps(result, ensure_ascii=False, indent=1))
    print("layers:", len(layers), "combos:", len(combos))
