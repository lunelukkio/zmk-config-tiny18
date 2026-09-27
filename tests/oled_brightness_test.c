/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "brightness.h"

static void test_seven_steps(void) {
    static const uint8_t contrast[] = {0x00, 0x01, 0x06, 0x0d, 0x20, 0x40, 0x7f};
    oled_brightness_t brightness;
    oled_brightness_init(&brightness, OLED_MAX_LEVEL);

    for (int level = OLED_MAX_LEVEL; level >= 0; level--) {
        assert(brightness.level == level);
        assert(oled_brightness_contrast(level) == contrast[level]);
        oled_brightness_command(&brightness, OLED_DOWN);
    }
    assert(brightness.level == 0);
    assert(!oled_brightness_visible(&brightness));
    oled_brightness_command(&brightness, OLED_UP);
    assert(brightness.level == 1);
    assert(oled_brightness_visible(&brightness));
}

static void test_legacy_settings(void) {
    static const uint8_t expected[] = {0, 2, 3, 4, 4, 5, 5, 5, 5, 6, 6, 6};
    for (uint8_t old = 0; old < sizeof(expected); old++) {
        assert(oled_brightness_from_legacy(old) == expected[old]);
    }
    assert(oled_brightness_from_legacy(12) == OLED_MAX_LEVEL);
}

int main(void) {
    test_seven_steps();
    test_legacy_settings();
    puts("OLED brightness tests passed");
    return 0;
}
