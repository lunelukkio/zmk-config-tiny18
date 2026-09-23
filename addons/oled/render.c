/*
 * Copyright (c) 2026 lunelukkio
 * SPDX-License-Identifier: MIT
 *
 * Draw one Tiny18 display state from the label data in layers.h.
 *
 * The drawing rules mirror draw_state() in docs/tools/make_oled_layers.py
 * (tiny18 repository) line for line, so the --preview PNG that script writes
 * is what the OLED shows: title doubled and centred with " +S", "+C", "+A",
 * "+G" appended for held modifiers, then one box per key with its label
 * doubled when a single short line fits, otherwise at one times. No rules are
 * drawn: empty rows set the title apart and the channel down the middle
 * separates the halves.
 *
 * Only this file includes layers.h: its tables are static, so a second
 * include would put a second copy in flash.
 */

#include "render.h"
#include "layers.h"

#define WIDTH 128
#define HEIGHT 64
#define GLYPH_W 3
#define GLYPH_H 5
#define GLYPH_GAP 1
#define TITLE_MAX (TINY18_TITLE_CHARS + 6)

static void set_pixel(uint8_t *frame, unsigned x, unsigned y) {
    if (x < WIDTH && y < HEIGHT) {
        frame[(y >> 3) * WIDTH + x] |= (uint8_t)(1U << (y & 7));
    }
}

/* Glyph strings are zero padded; count the leading non-zero entries. */
static unsigned text_len(const uint8_t *text, unsigned max) {
    unsigned len = 0;
    while (len < max && text[len] != 0) {
        len++;
    }
    return len;
}

static unsigned text_width(unsigned len, unsigned scale) {
    return len ? (len * (GLYPH_W + GLYPH_GAP) - GLYPH_GAP) * scale : 0;
}

static void draw_text(uint8_t *frame, unsigned x, unsigned y, const uint8_t *text, unsigned len, unsigned scale) {
    for (unsigned i = 0; i < len; i++) {
        const uint8_t *rows = tiny18_glyphs[text[i]];
        for (unsigned row = 0; row < GLYPH_H; row++) {
            for (unsigned col = 0; col < GLYPH_W; col++) {
                if (!((rows[row] >> (GLYPH_W - 1 - col)) & 1)) {
                    continue;
                }
                for (unsigned dy = 0; dy < scale; dy++) {
                    for (unsigned dx = 0; dx < scale; dx++) {
                        set_pixel(frame, x + col * scale + dx, y + row * scale + dy);
                    }
                }
            }
        }
        x += (GLYPH_W + GLYPH_GAP) * scale;
    }
}

static void draw_title(uint8_t *frame, uint8_t state) {
    uint8_t title[TITLE_MAX];
    unsigned len = text_len(tiny18_titles[state & TINY18_STATE_LAYER], TINY18_TITLE_CHARS);
    for (unsigned i = 0; i < len; i++) {
        title[i] = tiny18_titles[state & TINY18_STATE_LAYER][i];
    }
    if (state & (TINY18_STATE_SHIFT | TINY18_STATE_CTRL | TINY18_STATE_ALT | TINY18_STATE_GUI)) {
        title[len++] = TINY18_GLYPH_SPACE;
        title[len++] = TINY18_GLYPH_PLUS;
        if (state & TINY18_STATE_SHIFT) {
            title[len++] = TINY18_GLYPH_S;
        }
        if (state & TINY18_STATE_CTRL) {
            title[len++] = TINY18_GLYPH_C;
        }
        if (state & TINY18_STATE_ALT) {
            title[len++] = TINY18_GLYPH_A;
        }
        if (state & TINY18_STATE_GUI) {
            title[len++] = TINY18_GLYPH_G;
        }
    }
    draw_text(frame, (WIDTH - text_width(len, 2)) / 2, 1, title, len, 2);
}

static void draw_key(uint8_t *frame, unsigned x, unsigned y, const uint8_t lines[2][TINY18_LABEL_CHARS]) {
    for (unsigned dx = 0; dx < TINY18_BOX_W; dx++) {
        set_pixel(frame, x + dx, y);
        set_pixel(frame, x + dx, y + TINY18_BOX_H - 1);
    }
    for (unsigned dy = 0; dy < TINY18_BOX_H; dy++) {
        set_pixel(frame, x, y + dy);
        set_pixel(frame, x + TINY18_BOX_W - 1, y + dy);
    }

    unsigned len[2] = {text_len(lines[0], TINY18_LABEL_CHARS), text_len(lines[1], TINY18_LABEL_CHARS)};
    unsigned count = len[1] ? 2 : 1;
    /* A short single label is doubled so a letter reads from arm's length. */
    unsigned scale = (count == 1 && text_width(len[0], 2) <= TINY18_BOX_W - 4) ? 2 : 1;
    unsigned line_h = GLYPH_H * scale;
    unsigned top = y + (TINY18_BOX_H - (line_h * count + (count - 1))) / 2;
    for (unsigned i = 0; i < count; i++) {
        unsigned width = text_width(len[i], scale);
        draw_text(frame, x + (TINY18_BOX_W - width) / 2, top + i * (line_h + 1), lines[i], len[i], scale);
    }
}

void tiny18_render(uint8_t *frame, uint8_t state) {
    for (unsigned i = 0; i < TINY18_FRAME_BYTES; i++) {
        frame[i] = 0;
    }
    draw_title(frame, state);

    const uint8_t set = tiny18_state_set[state & (TINY18_STATE_LAYER | TINY18_STATE_SHIFT | TINY18_STATE_CTRL)];
    for (unsigned key = 0; key < TINY18_KEY_COUNT; key++) {
        draw_key(frame, tiny18_key_xy[key][0], tiny18_key_xy[key][1], tiny18_labels[set][key]);
    }
}
