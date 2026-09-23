# -*- coding: utf-8 -*-
"""Compose docs/keymap.html from the firmware keymap.

The body is a template; every key diagram, table and combo card, and every
key name quoted in the prose, is generated from config/tiny18.keymap so the
published page cannot drift from the firmware. Keys are called by what they
type in text-entry mode, never by position number.
"""
import hashlib, io, os, re, shutil, struct
from pathlib import Path
from gen_svg import (read_keymap, svg, label, held, POS, text_names, pair, PAGE_NAME,
                     PAGE_LONG, shifted, shift_face)

RIGHT_IMAGE = "tiny18-right.uf2"

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = str(Path(HERE).parent / "keymap.html")
# The one-sheet chart make_chart.py writes; it ships beside the page so the two
# can never drift apart.
CHART = Path(HERE).parent / "tiny18-keymap.png"

layers, combos = read_keymap()
L = dict(layers)
LNAME = [n for n, _ in layers]
NAMES = text_names(layers)
CD = dict((c["name"], c) for c in combos)

# which text-mode keys open each held page, e.g. {3: ['BackSpace'], 4: ['Space', 'N']}
HOLDERS = {}
for p, tok in enumerate(L["default_layer"]):
    m = re.match(r"&b?lt (\d+)", tok)
    if m:
        HOLDERS.setdefault(int(m.group(1)), []).append(NAMES[p])


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def keyname(tok):
    return label(tok)[0].replace("\n", " ")


def tap(layer, p):
    """First line of a key's label on a layer; a dead key reads as 無効キー."""
    t = label(L[layer][p])[0].split("\n")[0]
    return "無効キー" if t == "\u2014" else t


def keys(cname, sep=" + "):
    return pair(CD[cname]["pos"], NAMES, sep)


def mod_keys(layer, mod):
    """Text-mode names of the keys that hold a modifier on a layer, bare or
    as the hold of a mod-tap, e.g. 'A と M' for Ctrl in function mode."""
    return " と ".join(NAMES[p] for p, tok in enumerate(L[layer]) if held(tok) == mod)


def fig1():
    out = ['<svg viewBox="0 0 584 190" role="img" aria-label="キーの名前と position 番号">',
           '<text x="123" y="20" text-anchor="middle" font-size="13" fill="#5a6a72" font-family="sans-serif">左手側</text>',
           '<text x="435" y="20" text-anchor="middle" font-size="13" fill="#5a6a72" font-family="sans-serif">右手側</text>',
           '<line x1="266" y1="8" x2="266" y2="184" stroke="#ccc" stroke-dasharray="5 5" stroke-width="1.5"/>']
    short = {"BackSpace": "BkSp", "Space": "Spc", "Enter": "Ent"}
    for i in range(18):
        x, y = POS[i]
        nm = short.get(NAMES[i], NAMES[i])
        out.append('<rect x="%d" y="%d" width="48" height="48" rx="6" fill="#f6f8fa" stroke="#b8c2cc" stroke-width="1"/>' % (x, y))
        out.append('<text x="%d" y="%d" text-anchor="middle" font-size="%s" font-weight="bold" fill="#24292e" font-family="sans-serif">%s</text>'
                   % (x + 24, y + 24, "14" if len(nm) <= 2 else "11", nm))
        out.append('<text x="%d" y="%d" text-anchor="middle" font-size="9" fill="#8a949e" font-family="sans-serif">%d</text>' % (x + 24, y + 41, i))
    out.append('</svg>')
    return "\n".join(out)


# display name, layer, LED colour name, hex, switch combo, one-line description
MODES = [
    ("AI", "nav_layer", "青", "#1e6fd9", "mode_ai", "起動時のモード。左右とも逆 T 字の矢印、Escape、BackSpace。Shift で Tab・Delete と 2 つのコマンド。元に戻す・やり直す・切り取り・検索は右手の combo"),
    ("文字入力", "default_layer", "緑", "#22aa44", "mode_text", "毎日の文字入力"),
    ("数字キーパッド", "number_layer", "黄", "#d4a017", "mode_num", "左手がテンキー、右手が四則演算。Shift 中は移動・ロック・システムキー"),
    ("ゲーム", "game_layer", "シアン", "#17b8c4", "mode_game", "VRChat。WASD、I O P、Z X C、Esc と V。Shift を押さえると Esc が Z、V が R、Z X C が G M K に変わる。親指は Ctrl・Space・Space・Alt"),
    ("ファンクション", "fn_layer", "マゼンタ", "#b5389e", "mode_fn", "F1 から F12。Ctrl は %s の位置、Alt は %s の位置"
     % (mod_keys("fn_layer", "Ctrl"), mod_keys("fn_layer", "Alt"))),
    ("Bluetooth", "bluetooth_layer", "赤", "#dd2222", "mode_bt", "接続プロファイルの切り替え"),
]

FIGNO = [1]
CAPTION = {
    "default_layer": "文字入力モード。英字は入力結果の大小ではなくキー名として大文字で表す。左の親指 2 つがタップで BackSpace と Space、長押しで%sと%sを開く。" % (PAGE_LONG[6], PAGE_LONG[7]),
    "digit_symbol_layer": "%s を長押ししている間だけ。左手に 1 から 6、右手に 7 8 9 0 - =、右の親指に読点と句点。両端はタップで Enter、押さえると Shift。右の親指は Shift で ( ) になる。薄い色の左の親指は文字入力モードのまま。" % " か ".join(HOLDERS[6]),
    "edit_bracket_layer": "%s を長押ししている間だけ。Escape・括弧・Z X C V・句読点。Shift 中はEscapeがTabになり、通常のShift記号が出る。%s の位置はタップで Enter、押さえると Shift。薄い色の左の親指は文字入力モードのまま。" % (" か ".join(HOLDERS[7]), NAMES[13]),
    "nav_layer": "AI モード。矢印は左右とも逆 T 字。%s の位置は Escape、Shift 中は Tab。%s の位置は BackSpace、Shift 中は Delete。右手の上段は句点・↑・スラッシュ、ホーム行は ← ↓ → で、両端の . と / だけ Shift を押さえるとコマンドになる。%s と %s の位置はどちらもタップで Enter、押さえると Shift。親指 4 つの長押しは文字入力モードと同じ。" % (NAMES[0], NAMES[2], NAMES[6], NAMES[13]),
    "number_layer": "数字キーパッドモード。数字と小数点はテンキーのコードを送る。左手がテンキー配列、右手が四則演算と =・バックスラッシュ。%s の位置はタップで Enter、押さえると Shift。左の親指は 2 と 3、右の親指は 0 と小数点。" % NAMES[13],
    "game_layer": "ゲームモード。W が S の真上に来て WASD のダイヤ型になる。%s の位置が Escape、%s の位置が V、右上段は I O P、右のホーム行は Z X C。親指 4 つは Ctrl・Space・Space・Alt で、左の親指も文字入力モードとは違う。%s の位置は文字入力モードと同じ。" % (NAMES[0], NAMES[2], NAMES[13]),
    "fn_layer": "ファンクションモード。F キーは数字の面で同じ数字がある位置。%s の位置を押さえると Ctrl、%s の位置を押さえると Alt。%s の位置と薄い色の左の親指は文字入力モードと同じ。" % (mod_keys("fn_layer", "Ctrl"), mod_keys("fn_layer", "Alt"), NAMES[13]),
    "bluetooth_layer": "Bluetooth モード。プロファイル 5 つのうち BT 4 だけが右手にある。",
}


def figure(name):
    FIGNO[0] += 1
    return '%s\n<div class="figure-caption">図 %d. %s</div>' % (
        svg(L[name], name, base=L["default_layer"]),
        FIGNO[0], CAPTION[name])


def held_shift_figure(name, page):
    """Digit or ZXCV held page while one of its Shift keys is held."""
    FIGNO[0] += 1
    shifts = " か ".join(NAMES[p] for p, tok in enumerate(L[name]) if held(tok) == "Shift")
    if name == "digit_symbol_layer":
        caption = ("%sを開き、%s の位置で Shift を押さえている間。1 から = までの"
                   "12 キーは ! から + までの記号になり、右の親指は ( ) になる。"
                   % (page, shifts))
    else:
        caption = (
            "%sを開き、%s の位置で Shift を押さえている間。"
            "Escape は Tab になり、記号キーはそれぞれの Shift 側を表示する。"
            % (page, shifts)
        )
    return '%s\n<div class="figure-caption">図 %d. %s</div>' % (
        svg(shift_face(L[name]), name + "_shift", base=L["default_layer"]),
        FIGNO[0], caption)


def number_shift_figure():
    """Number mode while Shift is held: a second face, not a layer."""
    FIGNO[0] += 1
    b = [shifted(tok) for tok in L["number_layer"]]
    caption = ("数字キーパッドモードで %s の位置を押さえている間。左手が移動ブロック、"
               "右手がロックとシステムのキーになる。押さえていない 6 キー（左の小指、親指 4 つ、"
               "%s の位置）は変わらない。" % (NAMES[13], NAMES[13]))
    return '%s\n<div class="figure-caption">図 %d. %s</div>' % (
        svg(b, "number_layer_shift", base=L["default_layer"]), FIGNO[0], caption)


def game_shift_figure():
    """Game mode while Shift is held: a second face, not a layer.

    What changes and what stays are both read off the keymap, so the caption
    cannot keep naming a key the morphs no longer move."""
    FIGNO[0] += 1
    game = L["game_layer"]
    b = [shifted(tok) for tok in game]
    shifts = " か ".join(NAMES[p] for p, tok in enumerate(game) if held(tok) == "Shift")
    changed = "、".join("%s が %s" % (tap("game_layer", p), label(b[p])[0].split("\n")[0])
                       for p, tok in enumerate(game) if b[p] != tok)
    kept = [tap("game_layer", p) for p, tok in enumerate(game) if b[p] == tok]
    caption = ("ゲームモードで %s の位置を押さえている間。%s になる。変わったキーは Shift を外して"
               "単独キーとして送る。ほかの %d キー（%s）は変わらないので、走りながら動いて跳べる。"
               % (shifts, changed, len(kept), " ".join(kept)))
    return '%s\n<div class="figure-caption">図 %d. %s</div>' % (
        svg(b, "game_layer_shift", base=L["default_layer"]), FIGNO[0], caption)


def nav_shift_figure():
    """AI mode while Shift is held: Tab, Delete and two commands."""
    FIGNO[0] += 1
    b = [shifted(tok) for tok in L["nav_layer"]]
    caption = ("AI モードで %s か %s の位置を押さえている間。左上段の Escape と BackSpace は "
               "Tab と Delete になる。右手の上段は、両端の . と / だけが /model と /status に"
               "変わり、4 方向の矢印は変わらない。いずれも Shift を外して送るため、コマンドを"
               "送ると物理的に押した Shift も外れ、次のコマンドには Shift を押し直す。"
               % (NAMES[6], NAMES[13]))
    return '%s\n<div class="figure-caption">図 %d. %s</div>' % (
        svg(b, "nav_layer_shift", base=L["default_layer"]), FIGNO[0], caption)


def mode_table():
    rows = ['<table><tr><th style="width:8em;">モード</th><th style="width:4em;">LED</th>'
            '<th style="width:7em;">入り方</th><th>中身</th></tr>']
    for name, layer, col, hexcol, cname, desc in MODES:
        rows.append('<tr><td><strong>%s</strong></td>'
                    '<td><span class="led" style="background:%s;"></span>%s</td>'
                    '<td><code>%s</code></td><td>%s</td></tr>' % (name, hexcol, col, keys(cname), desc))
    rows.append('</table>')
    return "\n".join(rows)


def switch_table():
    """The switch keys, plus what they carry in the two modes most at risk."""
    rows = ['<table><tr><th style="width:9em;">押すキー</th><th style="width:9em;">行き先</th>'
            '<th style="width:11em;">数字キーパッドでは</th><th>ゲームモードでは</th></tr>']
    for name, layer, col, hexcol, cname, desc in MODES:
        c = CD[cname]

        def cell(mlayer):
            if LNAME.index(mlayer) not in c["layers"]:
                return "<strong>無効にしてある</strong>"
            return " と ".join(esc(tap(mlayer, p)) for p in c["pos"])

        rows.append('<tr><td><code>%s</code></td>'
                    '<td><span class="led" style="background:%s;"></span>%s モード</td>'
                    '<td>%s</td><td>%s</td></tr>'
                    % (keys(cname), hexcol, name, cell("number_layer"), cell("game_layer")))
    rows.append('</table>')
    return "\n".join(rows)


def led_table():
    rows = ['<table><tr><th style="width:6em;">色</th><th>何を示すか</th></tr>']
    for name, layer, col, hexcol, cname, desc in MODES:
        rows.append('<tr><td><span class="led" style="background:%s;"></span>%s</td>'
                    '<td>%s モード</td></tr>' % (hexcol, col, name))
    rows.append('<tr><td><span class="led" style="background:#ffffff;border:1px solid #bbb;"></span>白</td>'
                '<td>押しっぱなし面（%s、%s）を開いている間。指を離せば元のモードの色に戻る</td></tr>'
                % (PAGE_LONG[6], PAGE_LONG[7]))
    rows.append('</table>')
    return "\n".join(rows)


def letter_table():
    held = " か ".join(HOLDERS[7])
    return """<table>
<tr><th style="width:16em;">どこにあるか</th><th style="width:4em;">個数</th><th>文字</th></tr>
<tr><td>素のキー（タップ）</td><td>15</td><td><code>W E R U I O S D F J K L</code> と <code>A N M</code></td></tr>
<tr><td>文字入力モードの combo</td><td>6</td><td><code>Q T Y P G H</code></td></tr>
<tr><td>%s を長押ししたキー</td><td>4</td><td><code>Z X C V</code></td></tr>
<tr><td>%s を長押しした combo</td><td>1</td><td><code>B</code></td></tr>
<tr><td><strong>A から Z まで</strong></td><td><strong>26</strong></td><td>すべて打てる</td></tr>
</table>""" % (held, held)


# What a combo's output is for, where the key name alone does not say it.
COMBO_NOTE = {"Ctrl+Space": "日英切替"}


def combo_group(pairs, layer=None):
    """Cards for a set of combos, keyed by text-entry names unless a layer is
    given - inside one mode's own section the local names are what the reader
    is looking at."""
    out = []
    for n, desc in pairs:
        c = CD[n]
        ks = keys(n) if layer is None else " + ".join(
            esc(NAMES[p] + " の位置" if tap(layer, p) == "無効キー" else tap(layer, p))
            for p in c["pos"])
        name = keyname(c["binding"])
        note = COMBO_NOTE.get(name)
        out.append('<div class="combo-card"><div class="out">%s</div>'
                   '<div class="keys">%s</div><div class="desc">%s</div></div>'
                   % (esc(name) + ('<br><small>%s</small>' % note if note else ""), ks, desc))
    return '<div class="combo-grid">\n%s\n</div>' % "\n".join(out)


def on_page(cname):
    """e.g. ZXCV の面では C と V: what the combo keys are on the layer it lives on."""
    c = CD[cname]
    l = c["layers"][0]
    page = PAGE_LONG.get(l) or dict((LNAME.index(m[1]), m[0] + "モード") for m in MODES)[l]
    names = (NAMES[p] + " の位置" if tap(LNAME[l], p) == "無効キー"
             else tap(LNAME[l], p) for p in c["pos"])
    return "%sでは %s" % (page, " と ".join(esc(name) for name in names))


LEGEND = ('<div class="legend">'
          '<span><i class="sw" style="background:#eef6ff;border-color:#1e6fd9;"></i>文字・数字・記号</span>'
          '<span><i class="sw" style="background:#fdf2e9;border-color:#d35400;"></i>タップと長押しで二役</span>'
          '<span><i class="sw" style="background:#eefaf3;border-color:#2a9d8f;"></i>修飾キー</span>'
          '<span><i class="sw" style="background:#fff4e0;border-color:#b8860b;"></i>ショートカット</span>'
          '<span><i class="sw" style="background:#f3ecfb;border-color:#7a4fb5;"></i>レイヤー操作</span>'
          '<span><i class="sw" style="background:#f7f5ee;border-color:#c9c6b6;"></i>&mdash; 透過</span>'
          '<span><i class="sw" style="background:#f1f1ea;"></i>&mdash; 無効</span>'
          '</div>')

SUBS = {
    "FIG1": fig1(),
    "LEGEND": LEGEND,
    "MODE_TABLE": mode_table(),
    "SWITCH_TABLE": switch_table(),
    "LED_TABLE": led_table(),
    "LETTER_TABLE": letter_table(),
    "N_COMBOS": str(len(combos)),
    "HOLD3": " か ".join(HOLDERS[6]),
    "HOLD4": " か ".join(HOLDERS[7]),
    "PAGE3": PAGE_LONG[6],
    "PAGE4": PAGE_LONG[7],
    "LALT_KEYS": keys("lalt"),
    "LGUI_KEYS": keys("lgui"),
    "IME_KEYS": keys("ime"),
    "NUMLOCK_KEYS": keys("num_lock"),
    "DOT_KEYS": keys("num_dot_l"),
    "ZERO_KEYS": keys("num_zero_l"),
    "COMBO_LETTERS": combo_group([
        ("q", "上段の左 2 つ"), ("t", "上段の右 2 つ"),
        ("y", "右上段の左 2 つ"), ("p", "右上段の右 2 つ"),
        ("a", "ホームの S と D。A キーのタップでも出る"), ("g", "ホームの D と F"),
        ("h", "右ホームの J と K"),
    ]),
    "COMBO_NUMLAYER": combo_group([
        ("b", on_page("b")), ("n", on_page("n")),
    ]),
    "COMBO_MISC": combo_group([
        ("slash", "文字入力モードと %s の両方で効く" % PAGE_NAME[7]),
        ("lalt", "音声入力の起動用。人差し指の上段とホーム行。文字入力モードと AI モードで、打鍵後 150 ms おいてから"),
        ("lgui", "Windows キー。文字入力モードと AI モードで同じ。ゲームモードでも効き、そこでは %s"
         % " と ".join(tap("game_layer", p) for p in CD["lgui"]["pos"])),
        ("ime", "日本語と英語の切替（Ctrl+Space）。上段の薬指とホーム行の人差し指。文字入力モードだけ、打鍵後 150 ms おいてから"),
    ]),
    "COMBO_MODE": combo_group([
        ("mode_text", "文字入力モードへ"), ("mode_ai", "AI モードへ。ゲームモードでは無効"),
        ("mode_num", "数字モードへ"), ("mode_game", "ゲームモードへ。ゲームモードでは無効"),
        ("mode_fn", "ファンクションモードへ"), ("mode_bt", "Bluetooth モードへ"),
    ]),
    "COMBO_NUMBER": combo_group([
        ("num_zero_l", on_page("num_zero_l")),
        ("num_dot_l", on_page("num_dot_l")),
        ("num_lock", on_page("num_lock") + "。打鍵後 150 ms おいてから"),
    ]),
    "COMBO_NAV": combo_group([
        ("nav_copy", on_page("nav_copy")), ("nav_paste", on_page("nav_paste")),
        ("nav_undo", on_page("nav_undo")), ("nav_redo", on_page("nav_redo")),
        ("nav_cut", on_page("nav_cut")), ("nav_find", on_page("nav_find")),
    ]),
    "FIG_number_layer_shift": "",   # filled after the numbered figures below
    "FIG_game_layer_shift": "",     # filled after the numbered figures below
    "FIG_nav_layer_shift": "",       # filled after the numbered figures below
    "FIG_digit_symbol_layer_shift": "",  # filled after the numbered figures below
    "FIG_edit_bracket_layer_shift": "",  # filled after the numbered figures below
    "SW_num_shift_key": NAMES[13],
    "RIGHT_IMAGE": RIGHT_IMAGE,
}
for name, layer, col, hexcol, cname, desc in MODES:
    SUBS["SW_" + cname[5:]] = keys(cname)
# Numbered in the order body.html shows them, or the captions count out of turn.
for n in ("default_layer", "digit_symbol_layer", "edit_bracket_layer", "nav_layer",
          "number_layer", "fn_layer", "game_layer", "bluetooth_layer"):
    SUBS["FIG_" + n] = figure(n)
    if n == "digit_symbol_layer":
        SUBS["FIG_digit_symbol_layer_shift"] = held_shift_figure(n, PAGE_LONG[6])
    if n == "edit_bracket_layer":
        SUBS["FIG_edit_bracket_layer_shift"] = held_shift_figure(n, PAGE_LONG[7])
    if n == "number_layer":
        SUBS["FIG_number_layer_shift"] = number_shift_figure()
    if n == "game_layer":
        SUBS["FIG_game_layer_shift"] = game_shift_figure()
    if n == "nav_layer":
        SUBS["FIG_nav_layer_shift"] = nav_shift_figure()

# The sheet is around 15000 px tall at its own resolution, which buries the
# prose under screen after screen of scrolling, so the img tag shows it at a
# fixed CSS width and the file stays full size behind the link under it. The
# PNG is still wider than what the screen draws, so the displayed sheet is
# sharper than a 1:1 one would be.
#
# The width is set for the author's screen, which runs at 200% Windows
# scaling: one CSS pixel covers two device dots there, so 526 CSS px is 1052
# dots - the size the sheet was judged at. It was once written as a fraction
# of the PNG (0.375 of 1404); holding the CSS width instead means lowering S
# in make_chart.py changes the sharpness but never the size on the page.
# Read the real size off the PNG so a regenerated chart can never distort.
SHEET_CSS_W = 526
with io.open(CHART, "rb") as fh:
    header = fh.read(24)
sheet_w, sheet_h = struct.unpack(">II", header[16:24])
SHEET_FRACTION = SHEET_CSS_W / sheet_w
SUBS["SHEET_W"] = str(SHEET_CSS_W)
SUBS["SHEET_H"] = str(int(sheet_h * SHEET_FRACTION))
# The PNG keeps its file name and the server lets browsers cache it for four
# hours, so a regenerated chart stayed invisible behind the old one. A query
# built from the file's content changes whenever the picture does.
with io.open(CHART, "rb") as fh:
    SUBS["SHEET_V"] = hashlib.sha256(fh.read()).hexdigest()[:12]

def render_page():
    """Return the complete HTML without writing outside the documentation module."""
    with io.open(os.path.join(HERE, "head.html"), encoding="utf-8") as fh:
        head = fh.read()
    with io.open(os.path.join(HERE, "body.html"), encoding="utf-8") as fh:
        body = fh.read()
    for key, value in SUBS.items():
        body = body.replace("{{%s}}" % key, value)

    left = re.findall(r"\{\{(\w+)\}\}", body)
    assert not left, "unfilled placeholders: %s" % left
    # No bare position number may survive in the prose: "position 7" or
    # "14 を長押し".
    prose = re.sub(r"<svg.*?</svg>", "", body, flags=re.S)
    stray = re.findall(
        r"(?:position|位置) \d+|\b\d{1,2} (?:を|か|と) (?:長押し|押さえ)",
        prose,
    )
    assert not stray, "position numbers left in prose: %s" % stray
    return head + body


def write_page(site=SITE):
    """Write the rendered page and its generated images beside it."""
    output_dir = os.path.dirname(site)
    os.makedirs(output_dir, exist_ok=True)
    with io.open(site, "w", encoding="utf-8") as fh:
        fh.write(render_page())
    image_target = Path(output_dir) / CHART.name
    if image_target.resolve() != CHART.resolve():
        shutil.copyfile(CHART, image_target)
    print("wrote", site)
    print("figures:", FIGNO[0], "combos:", len(combos), "layers:", len(layers))


if __name__ == "__main__":
    write_page()
