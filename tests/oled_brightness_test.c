/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "brightness.h"

static void test_four_steps(void) {
    static const uint8_t contrast[] = {0x00, 0x01, 0x40, 0x7f};
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

static void test_saved_settings_migration(void) {
    static const uint8_t twelve[] = {0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3};
    static const uint8_t seven[] = {0, 1, 1, 1, 1, 2, 3};
    for (uint8_t old = 0; old < sizeof(twelve); old++) {
        assert(oled_brightness_from_twelve(old) == twelve[old]);
    }
    for (uint8_t old = 0; old < sizeof(seven); old++) {
        assert(oled_brightness_from_seven(old) == seven[old]);
    }
    assert(oled_brightness_from_twelve(12) == OLED_MAX_LEVEL);
    assert(oled_brightness_from_seven(7) == OLED_MAX_LEVEL);
}

int main(void) {
    test_four_steps();
    test_saved_settings_migration();
    puts("OLED brightness tests passed");
    return 0;
}
