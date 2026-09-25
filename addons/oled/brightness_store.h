/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#ifndef TINY18_BRIGHTNESS_STORE_H
#define TINY18_BRIGHTNESS_STORE_H
#include <stdbool.h>
#include <stdint.h>

uint8_t oled_store_load(void);
bool oled_store_save(uint8_t level);

#endif
