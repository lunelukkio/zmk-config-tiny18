/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#include "brightness.h"

static const uint8_t contrast[] = {
    0x00, 0x01, 0x40, 0x7f,
};

uint8_t oled_brightness_from_twelve(uint8_t level) {
    static const uint8_t old_to_new[] = {0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3};
    return level < sizeof(old_to_new) ? old_to_new[level] : OLED_MAX_LEVEL;
}

uint8_t oled_brightness_from_seven(uint8_t level) {
    static const uint8_t old_to_new[] = {0, 1, 1, 1, 1, 2, 3};
    return level < sizeof(old_to_new) ? old_to_new[level] : OLED_MAX_LEVEL;
}

uint8_t oled_brightness_contrast(uint8_t level) {
    return contrast[level <= OLED_MAX_LEVEL ? level : OLED_MAX_LEVEL];
}

void oled_brightness_init(oled_brightness_t *state, uint8_t saved_level) {
    state->level = saved_level == 0 || saved_level > OLED_MAX_LEVEL
                       ? OLED_MAX_LEVEL : saved_level;
    state->idle_off = false;
}

bool oled_brightness_visible(const oled_brightness_t *state) {
    return state->level != 0 && !state->idle_off;
}

void oled_brightness_idle(oled_brightness_t *state) {
    state->idle_off = true;
}

void oled_brightness_wake(oled_brightness_t *state) {
    if (state->idle_off) {
        state->idle_off = false;
        if (state->level == 0) {
            state->level = OLED_MAX_LEVEL;
        }
    }
}

bool oled_brightness_command(oled_brightness_t *state, uint8_t command) {
    if (command != OLED_ACTIVITY && command != OLED_DOWN &&
        command != OLED_UP && command != OLED_BOOT) {
        return false;
    }
    oled_brightness_wake(state);
    if (command == OLED_BOOT && state->level == 0) {
        state->level = OLED_MAX_LEVEL;
    }
    if (command == OLED_DOWN || command == OLED_UP) {
        if (command == OLED_DOWN && state->level > 0) {
            state->level--;
        }
        if (command == OLED_UP && state->level < OLED_MAX_LEVEL) {
            state->level++;
        }
    }
    return true;
}
