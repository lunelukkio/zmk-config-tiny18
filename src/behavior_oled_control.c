/* Copyright (c) 2026 The Tiny18 contributors
 * SPDX-License-Identifier: MIT
 */
#define DT_DRV_COMPAT tiny18_behavior_oled_control

#include <errno.h>
#include <drivers/behavior.h>
#include <zephyr/device.h>
#include <zmk/behavior.h>
#include "tiny18_oled_uart.h"

int tiny18_oled_send(uint8_t command);

static int on_pressed(struct zmk_behavior_binding *binding,
                      struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
    if (binding->param1 < 1 || binding->param1 > 2) {
        return -EINVAL;
    }
    const uint8_t command = TINY18_OLED_DOWN + binding->param1 - 1;
    return tiny18_oled_send(command) == 0 ? ZMK_BEHAVIOR_OPAQUE : -ENOSPC;
}

static int on_released(struct zmk_behavior_binding *binding,
                       struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int oled_control_init(const struct device *dev) {
    ARG_UNUSED(dev);
    return 0;
}

static const struct behavior_driver_api api = {
    .binding_pressed = on_pressed,
    .binding_released = on_released,
    .locality = BEHAVIOR_LOCALITY_CENTRAL,
};

BEHAVIOR_DT_INST_DEFINE(0, oled_control_init, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &api);
