# -*- coding: utf-8 -*-
"""Behavior tests for the public Tiny18 keymap diagrams."""

import unittest
import re

import build_html
import gen_svg
import make_chart
from gen_svg import read_keymap


class ChartModelTests(unittest.TestCase):
    def test_bluetooth_layer_has_a_labeled_led_mode_key(self):
        layers, _ = read_keymap()
        bindings = dict(layers)["bluetooth_layer"]

        self.assertEqual(bindings[0], "&led_mode")
        self.assertEqual(gen_svg.label(bindings[0]), ("LED", "bt"))

    def test_space_repeat_behavior_keeps_its_page_in_diagrams(self):
        layers, _ = read_keymap()
        self.assertEqual(dict(layers)["default_layer"][15], "&slt 7 SPACE")
        self.assertEqual(gen_svg.label("&slt 7 SPACE"), ("Space\nZXCV", "dual"))
        self.assertEqual(gen_svg.hold_pages(layers)[15], 7)

    def test_ai_is_first_and_held_pages_have_shift_faces(self):
        layers, combos = read_keymap()

        model = make_chart.chart_model(layers, combos)

        self.assertEqual(
            [section.name for section in model.sections[:8]],
            [
                "nav_layer",
                "nav_shift",
                "ai_command_layer",
                "default_layer",
                "digit_symbol_layer",
                "digit_symbol_shift",
                "edit_bracket_layer",
                "edit_bracket_shift",
            ],
        )

    def test_combo_cards_keep_information_from_removed_text_list(self):
        layers, combos = read_keymap()
        model = make_chart.chart_model(layers, combos)

        groups = make_chart.combo_card_groups(model, combos)
        cards = {
            card.name: card
            for group in groups
            for card in group.cards
        }

        self.assertEqual(set(cards), {combo["name"] for combo in combos})
        self.assertEqual(len(groups[0].cards), 13)
        for name in ("mode_text", "lalt", "ime"):
            self.assertIn("150ms", cards[name].note)
        self.assertIn("ZXCV", cards["slash"].note)

    def test_ai_combo_bindings_and_command_page(self):
        layers, combos = read_keymap()
        bindings = dict(layers)
        ai = bindings["nav_layer"]
        expected = {
            "ai_copy": ((0, 1), "&kp LC(C)"),
            "ai_paste": ((1, 2), "&kp LC(V)"),
            "ai_undo": ((0, 7), "&kp LC(Z)"),
            "ai_newline": ((2, 9), "&kp LC(J)"),
            "ai_redo": ((3, 10), "&kp LC(LS(Z))"),
            "ai_cut": ((3, 4), "&kp LC(X)"),
            "ai_find": ((5, 12), "&kp LC(F)"),
        }
        actual = {combo["name"]: (tuple(combo["pos"]), combo["binding"])
                  for combo in combos if combo["name"].startswith("ai_")}
        self.assertEqual(actual, expected)
        self.assertEqual(ai[4], "&kp UP_ARROW")
        self.assertEqual(ai[17], "&kp AT_SIGN")
        self.assertEqual(ai[15], "&slt 8 SPACE")
        self.assertEqual(bindings["ai_command_layer"][14], "&kp DELETE")
        self.assertEqual(bindings["ai_command_layer"][16], "&kp SLASH")
        self.assertEqual(
            {combo["name"]: (tuple(combo["pos"]), combo["binding"], tuple(combo["layers"]))
             for combo in combos if combo["name"].startswith("ime_")},
            {
                "ime_japanese": ((1, 8), "&kp LANG1", (0,)),
                "ime_english": ((0, 7), "&kp LANG2", (0,)),
            },
        )
        self.assertEqual(sum(2 in combo["layers"] for combo in combos), 13)

    def test_held_shift_faces_show_every_alternative_hold_position(self):
        layers, combos = read_keymap()
        sections = {
            section.name: section
            for section in make_chart.chart_model(layers, combos).sections
        }

        self.assertEqual(
            set(sections["digit_symbol_shift"].pressed_positions),
            {6, 13, 14},
        )
        self.assertEqual(
            set(sections["edit_bracket_shift"].pressed_positions),
            {13, 15, 16},
        )


class HtmlOutputTests(unittest.TestCase):
    def test_page_uses_the_simplified_current_diagrams_and_prose(self):
        page = build_html.render_page()

        self.assertIn('aria-label="digit_symbol_layer_shift"', page)
        self.assertIn('aria-label="edit_bracket_layer_shift"', page)
        self.assertIn("500 ms だけ表示する方式", page)
        self.assertIn("<code>LED</code>", page)
        self.assertIn("1 時間</strong>無操作", page)
        self.assertNotIn('aria-label="default_layer_shift"', page)
        self.assertNotIn("組み合わせて出す記号", page)
        self.assertNotIn("~ { } | : &quot; ? &lt; &gt;", page)
        self.assertNotIn("までの 12 キーに <code>!</code>", page)
        self.assertNotIn("大文字・小文字だけが変わる重複図", page)
        self.assertNotIn("通常キーの <code>A</code> は押し続ければ連打", page)
        self.assertNotIn("長押し側を「Escape を 1 回叩いて離す」", page)
        self.assertNotIn("右手上段の combo", page)
        self.assertNotIn("右手はフルキーボードの右側にあたる", page)
        self.assertIn("橙色の 6 つ", page)
        self.assertEqual(page.count('class="combo-card"'), 37)
        self.assertIn('aria-label="ai_command_layer"', page)
        self.assertIn("スラッシュと日英切替（6 個）", page)
        self.assertIn('<div class="out">NumLk</div>', page)
        self.assertLess(
            page.index("<td><strong>AI</strong></td>"),
            page.index("<td><strong>文字入力</strong></td>"),
        )

        default_svg = re.search(
            r'<svg[^>]+aria-label="default_layer".*?</svg>', page, re.S
        ).group(0)
        self.assertIn(">W<", default_svg)
        self.assertIn(">A<", default_svg)
        self.assertNotRegex(default_svg, r">[a-z]<")


if __name__ == "__main__":
    unittest.main()
