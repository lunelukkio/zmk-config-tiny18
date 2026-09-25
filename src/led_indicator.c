/*
 * Copyright (c) 2026 The Tiny18 contributors
 *
 * SPDX-License-Identifier: MIT
 */

#include <errno.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/led.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/settings/settings.h>

#include <zmk/activity.h>
#include <zmk/battery.h>
#include <zmk/ble.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/ble_active_profile_changed.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/keymap.h>
#include "led_indicator_state.h"

LOG_MODULE_REGISTER(tiny18_led, CONFIG_ZMK_LOG_LEVEL);

#define LED_PWM_NODE_ID DT_NODELABEL(tiny18_pwm_leds)

BUILD_ASSERT(DT_NODE_EXISTS(LED_PWM_NODE_ID), "Tiny18 PWM LED node is missing");
BUILD_ASSERT(CONFIG_TINY18_LED_BATTERY_LOW < CONFIG_TINY18_LED_BATTERY_HIGH,
             "Tiny18 low battery level must be below the high battery level");
BUILD_ASSERT(CONFIG_TINY18_LED_BATTERY_CRITICAL <= CONFIG_TINY18_LED_BATTERY_LOW,
             "Tiny18 critical battery level must not exceed the low battery level");

static const struct device *const led_dev = DEVICE_DT_GET(LED_PWM_NODE_ID);
static const uint8_t rgb_idx[] = {
    DT_NODE_CHILD_IDX(DT_NODELABEL(tiny18_pwm_red)),
    DT_NODE_CHILD_IDX(DT_NODELABEL(tiny18_pwm_green)),
    DT_NODE_CHILD_IDX(DT_NODELABEL(tiny18_pwm_blue)),
};

static const uint8_t layer_colors[] = {
    CONFIG_TINY18_LED_LAYER_0_COLOR,
    CONFIG_TINY18_LED_LAYER_1_COLOR,
    CONFIG_TINY18_LED_LAYER_2_COLOR,
    CONFIG_TINY18_LED_LAYER_3_COLOR,
    CONFIG_TINY18_LED_LAYER_4_COLOR,
    CONFIG_TINY18_LED_LAYER_5_COLOR,
    CONFIG_TINY18_LED_LAYER_6_COLOR,
    CONFIG_TINY18_LED_LAYER_7_COLOR,
    CONFIG_TINY18_LED_LAYER_8_COLOR,
};

enum boot_stage {
    BOOT_STAGE_BATTERY,
    BOOT_STAGE_BATTERY_NOTICE,
    BOOT_STAGE_GAP,
    BOOT_STAGE_CONNECTION_NOTICE,
    BOOT_STAGE_DONE,
};

enum dirty_setting {
    DIRTY_MODE = BIT(0),
    DIRTY_BRIGHTNESS = BIT(1),
};

struct led_runtime {
    struct tiny18_led_state output;
    enum boot_stage boot_stage;
    uint8_t battery_retries;
    uint8_t active_layer;
    uint8_t brightness;
    uint8_t channel_levels[3];
    uint8_t channel_valid_mask;
    uint8_t dirty_settings;
    bool settings_loaded;
    bool initialized;
};

static struct led_runtime runtime = {
    .output = {.mode = TINY18_LED_MODE_STEADY},
    .boot_stage = BOOT_STAGE_BATTERY,
    .brightness = 100,
};

static struct k_spinlock runtime_lock;
static struct k_work_delayable render_work;
static struct k_work_delayable layer_work;
static struct k_work_delayable save_work;

static uint8_t color_for_layer(uint8_t layer) {
    if (layer < ARRAY_SIZE(layer_colors)) {
        return layer_colors[layer];
    }
    return 0;
}

static uint8_t battery_color(uint8_t level) {
    if (level == 0) {
        return 5;
    }
    if (level >= CONFIG_TINY18_LED_BATTERY_HIGH) {
        return 2;
    }
    if (level >= CONFIG_TINY18_LED_BATTERY_LOW) {
        return 3;
    }
    return 1;
}

static uint8_t connection_color(void) {
    if (zmk_ble_active_profile_is_connected()) {
        return 4;
    }
    if (zmk_ble_active_profile_is_open()) {
        return 3;
    }
    return 1;
}

static void set_rgb_leds(uint8_t color, uint8_t brightness) {
    for (uint8_t pos = 0; pos < ARRAY_SIZE(rgb_idx); pos++) {
        const uint8_t bit = BIT(pos);
        const uint8_t level = (color & bit) ? brightness : 0;
        if ((runtime.channel_valid_mask & bit) && runtime.channel_levels[pos] == level) {
            continue;
        }
        const int rc = led_set_brightness(led_dev, rgb_idx[pos], level);
        if (rc != 0) {
            runtime.channel_valid_mask &= ~bit;
            LOG_ERR("Failed to set LED channel %u brightness (%d)", pos, rc);
            continue;
        }
        runtime.channel_levels[pos] = level;
        runtime.channel_valid_mask |= bit;
    }
}

static void schedule_render(k_timeout_t delay) {
    k_work_reschedule(&render_work, delay);
}

static void set_notice(uint8_t color, uint32_t duration_ms) {
    const int64_t now = k_uptime_get();
    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    runtime.output.notice_color = color;
    runtime.output.notice_deadline_ms = tiny18_led_deadline(now, duration_ms);
    k_spin_unlock(&runtime_lock, key);
    schedule_render(K_NO_WAIT);
}

static void update_layer(struct k_work *work) {
    ARG_UNUSED(work);
    const uint8_t layer = zmk_keymap_highest_layer_active();
    const uint8_t color = color_for_layer(layer);
    const int64_t now = k_uptime_get();
    bool changed = false;

    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    if (runtime.settings_loaded && runtime.active_layer != layer) {
        runtime.active_layer = layer;
        runtime.output.layer_color = color;
        if (runtime.boot_stage == BOOT_STAGE_DONE &&
            runtime.output.mode == TINY18_LED_MODE_PULSE) {
            runtime.output.pulse_deadline_ms =
                tiny18_led_deadline(now, CONFIG_TINY18_LED_PULSE_MS);
        }
        changed = true;
    }
    k_spin_unlock(&runtime_lock, key);

    if (changed) {
        schedule_render(K_NO_WAIT);
    }
}

static int layer_listener_cb(const zmk_event_t *eh) {
    ARG_UNUSED(eh);
    k_work_reschedule(&layer_work, K_MSEC(20));
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(tiny18_led_layer, layer_listener_cb);
ZMK_SUBSCRIPTION(tiny18_led_layer, zmk_layer_state_changed);

static int activity_listener_cb(const zmk_event_t *eh) {
    const struct zmk_activity_state_changed *ev = as_zmk_activity_state_changed(eh);
    if (ev == NULL) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    if (runtime.settings_loaded) {
        runtime.output.sleeping = (ev->state == ZMK_ACTIVITY_SLEEP);
        if (runtime.output.sleeping) {
            runtime.output.notice_color = 0;
            runtime.boot_stage = BOOT_STAGE_DONE;
        }
    }
    const bool ready = runtime.settings_loaded;
    k_spin_unlock(&runtime_lock, key);

    if (ready) {
        schedule_render(K_NO_WAIT);
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(tiny18_led_activity, activity_listener_cb);
ZMK_SUBSCRIPTION(tiny18_led_activity, zmk_activity_state_changed);

static int profile_listener_cb(const zmk_event_t *eh) {
    ARG_UNUSED(eh);

    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    const bool ready = runtime.settings_loaded && runtime.boot_stage == BOOT_STAGE_DONE;
    k_spin_unlock(&runtime_lock, key);

    if (ready) {
        set_notice(connection_color(), CONFIG_TINY18_LED_CONNECTION_BLINK_MS);
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(tiny18_led_profile, profile_listener_cb);
ZMK_SUBSCRIPTION(tiny18_led_profile, zmk_ble_active_profile_changed);

#if IS_ENABLED(CONFIG_ZMK_BATTERY_REPORTING)
static int battery_listener_cb(const zmk_event_t *eh) {
    const struct zmk_battery_state_changed *ev = as_zmk_battery_state_changed(eh);
    if (ev == NULL || ev->state_of_charge == 0 ||
        ev->state_of_charge > CONFIG_TINY18_LED_BATTERY_CRITICAL) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    const bool ready = runtime.settings_loaded && runtime.boot_stage == BOOT_STAGE_DONE;
    k_spin_unlock(&runtime_lock, key);

    if (ready) {
        set_notice(1, CONFIG_TINY18_LED_BATTERY_BLINK_MS);
    }
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(tiny18_led_battery, battery_listener_cb);
ZMK_SUBSCRIPTION(tiny18_led_battery, zmk_battery_state_changed);
#endif

static void save_settings_work_cb(struct k_work *work) {
    ARG_UNUSED(work);
    uint8_t mode;
    uint8_t brightness;
    uint8_t dirty;

    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    mode = (uint8_t)runtime.output.mode;
    brightness = runtime.brightness;
    dirty = runtime.dirty_settings;
    runtime.dirty_settings = 0;
    k_spin_unlock(&runtime_lock, key);

    if (dirty & DIRTY_MODE) {
        const int rc = settings_save_one("tiny18_led/mode", &mode, sizeof(mode));
        if (rc != 0) {
            dirty |= DIRTY_MODE;
            LOG_ERR("Failed to save LED mode (%d)", rc);
        } else {
            dirty &= ~DIRTY_MODE;
        }
    }
    if (dirty & DIRTY_BRIGHTNESS) {
        const int rc = settings_save_one("tiny18_led/brightness", &brightness, sizeof(brightness));
        if (rc != 0) {
            LOG_ERR("Failed to save LED brightness (%d)", rc);
        } else {
            dirty &= ~DIRTY_BRIGHTNESS;
        }
    }
    if (dirty != 0) {
        key = k_spin_lock(&runtime_lock);
        runtime.dirty_settings |= dirty;
        k_spin_unlock(&runtime_lock, key);
        k_work_reschedule(&save_work, K_MSEC(CONFIG_TINY18_LED_SETTINGS_SAVE_DEBOUNCE_MS));
    }
}

static void render_work_cb(struct k_work *work) {
    ARG_UNUSED(work);
    struct led_runtime snapshot;
    int64_t now = k_uptime_get();

    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    if (!runtime.initialized) {
        k_spin_unlock(&runtime_lock, key);
        return;
    }
    snapshot = runtime;
    k_spin_unlock(&runtime_lock, key);

    if (snapshot.boot_stage == BOOT_STAGE_BATTERY) {
        uint8_t level = zmk_battery_state_of_charge();
        if (level == 0 && snapshot.battery_retries < 10) {
            key = k_spin_lock(&runtime_lock);
            runtime.battery_retries++;
            k_spin_unlock(&runtime_lock, key);
            set_rgb_leds(0, snapshot.brightness);
            schedule_render(K_MSEC(100));
            return;
        }

        key = k_spin_lock(&runtime_lock);
        runtime.output.notice_color = battery_color(level);
        runtime.output.notice_deadline_ms =
            tiny18_led_deadline(now, CONFIG_TINY18_LED_BATTERY_BLINK_MS);
        runtime.boot_stage = BOOT_STAGE_BATTERY_NOTICE;
        snapshot = runtime;
        k_spin_unlock(&runtime_lock, key);
    } else if (snapshot.boot_stage == BOOT_STAGE_BATTERY_NOTICE &&
               now >= snapshot.output.notice_deadline_ms) {
        key = k_spin_lock(&runtime_lock);
        runtime.output.notice_color = 0;
        runtime.boot_stage = BOOT_STAGE_GAP;
        runtime.output.notice_deadline_ms =
            tiny18_led_deadline(now, CONFIG_TINY18_LED_INTERVAL_MS);
        snapshot = runtime;
        k_spin_unlock(&runtime_lock, key);
    } else if (snapshot.boot_stage == BOOT_STAGE_GAP &&
               now >= snapshot.output.notice_deadline_ms) {
        const uint8_t color = connection_color();
        key = k_spin_lock(&runtime_lock);
        runtime.output.notice_color = color;
        runtime.boot_stage = BOOT_STAGE_CONNECTION_NOTICE;
        runtime.output.notice_deadline_ms =
            tiny18_led_deadline(now, CONFIG_TINY18_LED_CONNECTION_BLINK_MS);
        snapshot = runtime;
        k_spin_unlock(&runtime_lock, key);
    } else if (snapshot.boot_stage == BOOT_STAGE_CONNECTION_NOTICE &&
               now >= snapshot.output.notice_deadline_ms) {
        key = k_spin_lock(&runtime_lock);
        runtime.output.notice_color = 0;
        runtime.boot_stage = BOOT_STAGE_DONE;
        if (runtime.output.mode == TINY18_LED_MODE_PULSE) {
            runtime.output.pulse_deadline_ms =
                tiny18_led_deadline(now, CONFIG_TINY18_LED_PULSE_MS);
        }
        snapshot = runtime;
        k_spin_unlock(&runtime_lock, key);
    }

    now = k_uptime_get();
    const uint8_t color = tiny18_led_evaluate(&snapshot.output, now);
    set_rgb_leds(color, snapshot.brightness);

    int64_t next_deadline = 0;
    if (snapshot.boot_stage != BOOT_STAGE_DONE) {
        next_deadline = snapshot.output.notice_deadline_ms;
    } else if (snapshot.output.notice_color > 0 &&
               snapshot.output.notice_deadline_ms > now) {
        next_deadline = snapshot.output.notice_deadline_ms;
    } else if (snapshot.output.mode == TINY18_LED_MODE_PULSE &&
               snapshot.output.pulse_deadline_ms > now) {
        next_deadline = snapshot.output.pulse_deadline_ms;
    }

    if (next_deadline > now) {
        schedule_render(K_MSEC(next_deadline - now));
    }
}

static int led_settings_set(const char *name, size_t len, settings_read_cb read_cb,
                            void *cb_arg) {
    const char *next;
    bool mode_key = settings_name_steq(name, "mode", &next) && next == NULL;
    bool brightness_key = settings_name_steq(name, "brightness", &next) && next == NULL;
    if (!mode_key && !brightness_key) {
        return -ENOENT;
    }
    if (len != sizeof(uint8_t)) {
        return -EINVAL;
    }

    uint8_t value;
    const int rc = read_cb(cb_arg, &value, sizeof(value));
    if (rc < 0) {
        return rc;
    }
    if (rc != (int)sizeof(value)) {
        return -EINVAL;
    }

    if (mode_key) {
        enum tiny18_led_mode mode;
        if (!tiny18_led_mode_from_value(value, &mode)) {
            LOG_WRN("Ignoring invalid saved LED mode %u", value);
            return 0;
        }
        k_spinlock_key_t key = k_spin_lock(&runtime_lock);
        runtime.output.mode = mode;
        k_spin_unlock(&runtime_lock, key);
    } else if (!tiny18_led_brightness_valid(value)) {
        LOG_WRN("Ignoring invalid saved LED brightness %u", value);
        return 0;
    } else {
        k_spinlock_key_t key = k_spin_lock(&runtime_lock);
        runtime.brightness = value;
        k_spin_unlock(&runtime_lock, key);
    }
    return 0;
}

static int led_settings_commit(void) {
    const uint8_t layer = zmk_keymap_highest_layer_active();
    const int64_t now = k_uptime_get();
    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    runtime.settings_loaded = true;
    runtime.initialized = true;
    runtime.active_layer = layer;
    runtime.output.layer_color = color_for_layer(layer);
    runtime.output.sleeping = false;
    runtime.output.notice_color = 0;
    runtime.battery_retries = 0;
    runtime.boot_stage = BOOT_STAGE_BATTERY;
    if (runtime.output.mode == TINY18_LED_MODE_PULSE) {
        runtime.output.pulse_deadline_ms = tiny18_led_deadline(now, CONFIG_TINY18_LED_PULSE_MS);
    }
    k_spin_unlock(&runtime_lock, key);

    schedule_render(K_NO_WAIT);
    return 0;
}

SETTINGS_STATIC_HANDLER_DEFINE(tiny18_led, "tiny18_led", NULL, led_settings_set,
                               led_settings_commit, NULL);

void tiny18_led_mode_toggle(void) {
    const int64_t now = k_uptime_get();
    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    if (!runtime.settings_loaded) {
        k_spin_unlock(&runtime_lock, key);
        return;
    }

    if (runtime.output.mode == TINY18_LED_MODE_STEADY) {
        runtime.output.mode = TINY18_LED_MODE_PULSE;
        runtime.output.pulse_deadline_ms =
            tiny18_led_deadline(now, CONFIG_TINY18_LED_PULSE_MS);
    } else {
        runtime.output.mode = TINY18_LED_MODE_STEADY;
        runtime.output.pulse_deadline_ms = 0;
    }
    runtime.dirty_settings |= DIRTY_MODE;
    k_spin_unlock(&runtime_lock, key);

    k_work_reschedule(&save_work, K_MSEC(CONFIG_TINY18_LED_SETTINGS_SAVE_DEBOUNCE_MS));
    schedule_render(K_NO_WAIT);
}

void tiny18_led_brightness_step(bool increase) {
    const int64_t now = k_uptime_get();
    k_spinlock_key_t key = k_spin_lock(&runtime_lock);
    if (!runtime.settings_loaded) {
        k_spin_unlock(&runtime_lock, key);
        return;
    }

    const uint8_t next = tiny18_led_next_brightness(runtime.brightness, increase);
    const bool changed = next != runtime.brightness;
    runtime.brightness = next;
    if (changed) {
        runtime.dirty_settings |= DIRTY_BRIGHTNESS;
    }
    if (runtime.boot_stage == BOOT_STAGE_DONE && runtime.output.mode == TINY18_LED_MODE_PULSE) {
        runtime.output.pulse_deadline_ms = next > 0
                                               ? tiny18_led_deadline(now, CONFIG_TINY18_LED_PULSE_MS)
                                               : 0;
    }
    k_spin_unlock(&runtime_lock, key);

    if (changed) {
        k_work_reschedule(&save_work, K_MSEC(CONFIG_TINY18_LED_SETTINGS_SAVE_DEBOUNCE_MS));
    }
    schedule_render(K_NO_WAIT);
}

static int tiny18_led_init(void) {
    if (!device_is_ready(led_dev)) {
        LOG_ERR("LED device is not ready");
        return -ENODEV;
    }

    k_work_init_delayable(&render_work, render_work_cb);
    k_work_init_delayable(&layer_work, update_layer);
    k_work_init_delayable(&save_work, save_settings_work_cb);
    set_rgb_leds(0, 0);
    return 0;
}

SYS_INIT(tiny18_led_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
