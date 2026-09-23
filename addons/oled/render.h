/*
 * Copyright (c) 2026 lunelukkio
 * SPDX-License-Identifier: MIT
 *
 * Draw one Tiny18 display state into an SSD1306 frame buffer.
 *
 * The state byte is what the keyboard sends: the highest active layer in
 * bits 0-2 and one bit per held modifier. Bit 7 is never set by the
 * keyboard, which lets the receiver reject line noise.
 */
#ifndef TINY18_RENDER_H
#define TINY18_RENDER_H

#include <stdint.h>

#define TINY18_STATE_LAYER 0x07
#define TINY18_STATE_SHIFT 0x08
#define TINY18_STATE_CTRL 0x10
#define TINY18_STATE_ALT 0x20
#define TINY18_STATE_GUI 0x40
#define TINY18_STATE_INVALID 0x80

#define TINY18_FRAME_BYTES 1024

/* frame is 128x64 in SSD1306 page order: 128 bytes per page, bit 0 on top. */
void tiny18_render(uint8_t *frame, uint8_t state);

#endif
