/*
 * Copyright (c) 2026 lunelukkio
 * SPDX-License-Identifier: MIT
 *
 * Draw one Tiny18 display state into an SSD1306 frame buffer.
 *
 * The receiver passes a complete decoded layer/left/right modifier state.
 */
#ifndef TINY18_RENDER_H
#define TINY18_RENDER_H

#include <stdint.h>

typedef struct {
    uint8_t layer;
    uint8_t left_mods;
    uint8_t right_mods;
} tiny18_display_state_t;

#define TINY18_FRAME_BYTES 1024

/* frame is 128x64 in SSD1306 page order: 128 bytes per page, bit 0 on top. */
void tiny18_render(uint8_t *frame, tiny18_display_state_t state);

#endif
