/*
 * Copyright (c) 2026 The Tiny18 contributors
 *
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum tiny18_led_mode {
    TINY18_LED_MODE_STEADY = 0,
    TINY18_LED_MODE_PULSE = 1,
};

struct tiny18_led_state {
    enum tiny18_led_mode mode;
    uint8_t layer_color;
    int64_t pulse_deadline_ms;
    uint8_t notice_color;
    int64_t notice_deadline_ms;
    bool sleeping;
};

uint8_t tiny18_led_evaluate(const struct tiny18_led_state *state, int64_t now_ms);
bool tiny18_led_mode_from_value(uint8_t value, enum tiny18_led_mode *mode);
bool tiny18_led_brightness_valid(uint8_t value);
uint8_t tiny18_led_next_brightness(uint8_t current, bool increase);
int64_t tiny18_led_deadline(int64_t now_ms, uint32_t duration_ms);
