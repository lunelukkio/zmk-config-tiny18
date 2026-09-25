/*
 * Copyright (c) 2026 The Tiny18 contributors
 *
 * SPDX-License-Identifier: MIT
 */

#include "led_indicator_state.h"

static const uint8_t brightness_levels[] = {0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100};

uint8_t tiny18_led_evaluate(const struct tiny18_led_state *state, int64_t now_ms) {
    if (state->sleeping) {
        return 0;
    }

    if (state->notice_color > 0 && now_ms < state->notice_deadline_ms) {
        return state->notice_color;
    }

    if (state->mode == TINY18_LED_MODE_STEADY) {
        return state->layer_color;
    }

    if (state->mode == TINY18_LED_MODE_PULSE && now_ms < state->pulse_deadline_ms) {
        return state->layer_color;
    }

    return 0;
}

bool tiny18_led_mode_from_value(uint8_t value, enum tiny18_led_mode *mode) {
    if (value > TINY18_LED_MODE_PULSE) {
        return false;
    }

    *mode = (enum tiny18_led_mode)value;
    return true;
}

bool tiny18_led_brightness_valid(uint8_t value) {
    for (size_t i = 0; i < sizeof(brightness_levels) / sizeof(brightness_levels[0]); i++) {
        if (brightness_levels[i] == value) {
            return true;
        }
    }
    return false;
}

uint8_t tiny18_led_next_brightness(uint8_t current, bool increase) {
    for (size_t i = 0; i < sizeof(brightness_levels) / sizeof(brightness_levels[0]); i++) {
        if (brightness_levels[i] != current) {
            continue;
        }
        if (increase && i + 1 < sizeof(brightness_levels) / sizeof(brightness_levels[0])) {
            return brightness_levels[i + 1];
        }
        if (!increase && i > 0) {
            return brightness_levels[i - 1];
        }
        return current;
    }
    return 100;
}

int64_t tiny18_led_deadline(int64_t now_ms, uint32_t duration_ms) {
    return now_ms + (int64_t)duration_ms;
}
