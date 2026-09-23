# -*- coding: utf-8 -*-
"""Behavior tests for the public Tiny18 keymap diagrams."""

import unittest
import re

import build_html
import gen_svg
import make_chart
from gen_svg import read_keymap


class ChartModelTests(unittest.TestCase):
    def test_space_repeat_behavior_keeps_its_page_in_diagrams(self):
        layers, _ = read_keymap()
        self.assertEqual(dict(layers)["default_layer"][15], "&slt 7 SPACE")
        self.assertEqual(gen_svg.label("&slt 7 SPACE"), ("Space\nZXCV", "dual"))
        self.assertEqual(gen_svg.hold_pages(layers)[15], 7)

    def test_ai_is_first_and_held_pages_have_shift_faces(self):
        layers, combos = read_keymap()

        model = make_chart.chart_model(layers, combos)

        self.assertEqual(
            [section.name for section in model.sections[:7]],
            [
                "nav_layer",
                "nav_shift",
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
        for name in ("mode_text", "lalt", "ime", "nav_copy", "nav_paste",
                     "nav_undo", "nav_redo", "nav_cut", "nav_find"):
            self.assertIn("150ms", cards[name].note)
        self.assertIn("ZXCV", cards["slash"].note)

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
        self.assertEqual(page.count('class="combo-card"'), 28)
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
