"""Check letter case at the shared labels, OLED states, and glyph boundary."""

import unittest

import gen_svg
import make_oled_layers as oled


class LetterCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layers, _ = gen_svg.read_keymap()
        cls.sets, cls.mapping = oled.label_sets(cls.layers, "3x3")
        cls.positions = [p for p, _, _ in oled.layout_3x3()[0]]

    def labels(self, layer, mods=0):
        return dict(zip(self.positions, self.sets[self.mapping[layer | mods]]))

    def test_text_letters_are_always_shown_upper_case(self):
        # The display names a key; it does not report the lower/upper case
        # the host is about to receive, so Shift no longer changes this.
        for mods in (0, oled.STATE_SHIFT):
            labels = self.labels(0, mods)
            actual = "".join(labels[p][0] for p in (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 6))
            self.assertEqual(actual, "WERUIOSDFJKLA")
            self.assertEqual(labels[6], ["A", "SFT"])
            self.assertEqual(labels[16], ["N", "ZXCV"])
            self.assertEqual(labels[17], ["M", "CTL"])

    def test_ctrl_shows_upper_case_letter_and_title_flags(self):
        self.assertEqual(self.labels(0, oled.STATE_CTRL)[0], ["^W"])
        self.assertEqual(self.labels(0, oled.STATE_CTRL | oled.STATE_SHIFT)[0], ["^W"])
        self.assertEqual(oled.title_text(0, oled.STATE_CTRL | oled.STATE_SHIFT), "TEXT +SC")

    def test_zxcv_page_letters_stay_upper_while_symbols_still_shift(self):
        for mods in (0, oled.STATE_SHIFT):
            labels = self.labels(7, mods)
            self.assertEqual("".join(labels[p][0] for p in (6, 7, 8, 9)), "ZXCV")
        self.assertEqual(self.labels(7)[0], ["ESC"])
        self.assertEqual(self.labels(7, oled.STATE_SHIFT)[0], ["TAB"])
        self.assertEqual(self.labels(7, oled.STATE_SHIFT)[12], ["?"])
        self.assertEqual(self.labels(7, oled.STATE_CTRL)[6], ["^Z"])

    def test_ai_arrows_stay_plain_under_shift_and_game_names_keep_case(self):
        for mods in (0, oled.STATE_SHIFT):
            self.assertEqual([self.labels(2, mods)[p] for p in (4, 10, 11, 12)],
                             [["↑"], ["←"], ["↓"], ["→"]])
        self.assertEqual(self.labels(2)[3], ["."])
        self.assertEqual(self.labels(2)[5], ["/"])
        self.assertEqual(self.labels(2, oled.STATE_SHIFT)[3], ["/MOD"])
        self.assertEqual(self.labels(2, oled.STATE_SHIFT)[5], ["/STA"])
        self.assertEqual(self.labels(5)[1], ["W"])

    def test_shared_formatter_changes_only_letter_taps(self):
        self.assertEqual(gen_svg.format_letter_label("A\nShift", "lower"), "a\nShift")
        self.assertEqual(gen_svg.format_letter_label("N\nZXCV", "pair"), "n/N\nZXCV")
        for label in ("Ctrl+Z", "Ctrl+Shift+Z", "/model", "Shift", "F1"):
            self.assertEqual(gen_svg.format_letter_label(label, "lower"), label)
        self.assertEqual(gen_svg.text_names(self.layers)[0], "W")

    def test_lowercase_glyphs_remain_distinct_in_the_font(self):
        # No label uses a lowercase letter any more (letters are always drawn
        # upper case), so glyph_table() only indexes the upper case half. The
        # font itself still carries a distinct lowercase glyph per letter,
        # checked directly here rather than through the header's used-glyph
        # index, in case a future label needs the distinction again.
        for char in "abcdefghijklmnopqrstuvwxyz":
            rows = oled.glyph_rows(char)
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(0 <= row < 8 for row in rows))
            self.assertNotEqual(rows, oled.glyph_rows(char.upper()))
        self.assertNotEqual(oled.glyph_rows("i"), oled.glyph_rows("l"))
        self.assertNotEqual(oled.glyph_rows("m"), oled.glyph_rows("n"))
        glyphs = oled.glyph_table(self.sets)
        self.assertFalse(set("abcdefghijklmnopqrstuvwxyz") & set(glyphs))

    def test_all_layouts_render_all_states_without_overflow(self):
        for layout in oled.LAYOUTS:
            sets, mapping = oled.label_sets(self.layers, layout)
            oled.glyph_table(sets)
            for state in range(oled.LABEL_STATES):
                frame = oled.draw_state(sets[mapping[state]], state & 7, state, layout)
                self.assertEqual(frame.size, (128, 64))


if __name__ == "__main__":
    unittest.main()
