/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#ifndef TINY18_BRIGHTNESS_H
#define TINY18_BRIGHTNESS_H
#include <stdbool.h>
#include <stdint.h>

enum { OLED_ACTIVITY = 0x80, OLED_DOWN = 0x82, OLED_UP, OLED_BOOT };
enum { OLED_MAX_LEVEL = 11 };

typedef struct {
    uint8_t level;
    bool idle_off;
} oled_brightness_t;

void oled_brightness_init(oled_brightness_t *state, uint8_t saved_level);
bool oled_brightness_command(oled_brightness_t *state, uint8_t command);
void oled_brightness_idle(oled_brightness_t *state);
void oled_brightness_wake(oled_brightness_t *state);
bool oled_brightness_visible(const oled_brightness_t *state);
uint8_t oled_brightness_contrast(uint8_t level);

#endif
