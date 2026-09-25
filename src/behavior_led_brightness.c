/*
 * Copyright (c) 2026 The Tiny18 contributors
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT tiny18_behavior_led_brightness

#include <errno.h>
#include <stdbool.h>

#include <drivers/behavior.h>
#include <zephyr/device.h>

#include <zmk/behavior.h>

void tiny18_led_brightness_step(bool increase);

static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
    if (binding->param1 > 1) {
        return -EINVAL;
    }
    tiny18_led_brightness_step(binding->param1 == 1);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int on_keymap_binding_released(struct zmk_behavior_binding *binding,
                                      struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    return ZMK_BEHAVIOR_OPAQUE;
}

static int behavior_led_brightness_init(const struct device *dev) {
    ARG_UNUSED(dev);
    return 0;
}

#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
static const struct behavior_parameter_value_metadata direction_values[] = {
    {.display_name = "Decrease Brightness", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 0},
    {.display_name = "Increase Brightness", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 1},
};

static const struct behavior_parameter_metadata_set direction_set = {
    .param1_values = direction_values,
    .param1_values_len = ARRAY_SIZE(direction_values),
};

static const struct behavior_parameter_metadata metadata = {
    .sets = &direction_set,
    .sets_len = 1,
};
#endif

static const struct behavior_driver_api behavior_led_brightness_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .binding_released = on_keymap_binding_released,
    .locality = BEHAVIOR_LOCALITY_CENTRAL,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .parameter_metadata = &metadata,
#endif
};

BEHAVIOR_DT_INST_DEFINE(0, behavior_led_brightness_init, NULL, NULL, NULL, POST_KERNEL,
                        CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_led_brightness_driver_api);
