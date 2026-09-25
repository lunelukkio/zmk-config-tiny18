/*
 * Copyright (c) 2026 The Tiny18 contributors
 *
 * SPDX-License-Identifier: MIT
 */

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "led_indicator_state.h"

static void test_pulse_expires_at_deadline(void) {
    const struct tiny18_led_state state = {
        .mode = TINY18_LED_MODE_PULSE,
        .layer_color = 4,
        .pulse_deadline_ms = 500,
    };

    assert(tiny18_led_evaluate(&state, 499) == 4);
    assert(tiny18_led_evaluate(&state, 500) == 0);
}

static void test_steady_mode_has_no_expiry(void) {
    const struct tiny18_led_state state = {
        .mode = TINY18_LED_MODE_STEADY,
        .layer_color = 2,
        .pulse_deadline_ms = 1,
    };

    assert(tiny18_led_evaluate(&state, 3600000) == 2);
}

static void test_notice_overrides_then_restores_layer_mode(void) {
    const struct tiny18_led_state state = {
        .mode = TINY18_LED_MODE_PULSE,
        .layer_color = 4,
        .pulse_deadline_ms = 500,
        .notice_color = 2,
        .notice_deadline_ms = 2000,
    };

    assert(tiny18_led_evaluate(&state, 1999) == 2);
    assert(tiny18_led_evaluate(&state, 2000) == 0);
}

static void test_notice_then_steady_layer(void) {
    const struct tiny18_led_state state = {
        .mode = TINY18_LED_MODE_STEADY,
        .layer_color = 1,
        .notice_color = 4,
        .notice_deadline_ms = 2000,
    };

    assert(tiny18_led_evaluate(&state, 1999) == 4);
    assert(tiny18_led_evaluate(&state, 2000) == 1);
}

static void test_sleep_suppresses_all_output(void) {
    const struct tiny18_led_state state = {
        .mode = TINY18_LED_MODE_STEADY,
        .layer_color = 1,
        .notice_color = 4,
        .notice_deadline_ms = 2000,
        .sleeping = true,
    };

    assert(tiny18_led_evaluate(&state, 1000) == 0);
}

static void test_pulse_deadline_starts_from_latest_change(void) {
    assert(tiny18_led_deadline(1000, 500) == 1500);
    assert(tiny18_led_deadline(1400, 500) == 1900);
}

static void test_mode_setting_validation(void) {
    enum tiny18_led_mode mode = TINY18_LED_MODE_STEADY;

    assert(tiny18_led_mode_from_value(0, &mode));
    assert(mode == TINY18_LED_MODE_STEADY);
    assert(tiny18_led_mode_from_value(1, &mode));
    assert(mode == TINY18_LED_MODE_PULSE);
    assert(!tiny18_led_mode_from_value(2, &mode));
}

int main(void) {
    test_pulse_expires_at_deadline();
    test_steady_mode_has_no_expiry();
    test_notice_overrides_then_restores_layer_mode();
    test_notice_then_steady_layer();
    test_sleep_suppresses_all_output();
    test_pulse_deadline_starts_from_latest_change();
    test_mode_setting_validation();
    puts("LED indicator state tests passed");
    return 0;
}
