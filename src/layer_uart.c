/*
 * Send Tiny18's display state through UART1.
 *
 * The external display is deliberately a separate USB-powered device.  A
 * state frames travel from the right-half XIAO's D1 TX pin to its receiver;
 * no keyboard power or host-facing data path is involved.
 *
 * Three-byte frames carry layer and left/right modifiers. Bytes 0x80-0x84
 * carry activity, OLED controls and a keyboard boot notice.
 *
 * The current state goes out at boot, on layer and modifier changes, and on
 * key presses. Each frame is one queue record; controls are one-byte records.
 *
 * Listeners enqueue records without blocking. A worker reads modifier state
 * after event processing; a dedicated thread writes complete records to UART.
 */

#include <errno.h>

#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>

#include <zmk/event_manager.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>
#include <zmk/keys.h>
#include "tiny18_oled_uart.h"

static const struct device *const layer_uart = DEVICE_DT_GET(DT_NODELABEL(uart1));
struct oled_record {
    uint8_t length;
    uint8_t bytes[3];
};
K_MSGQ_DEFINE(oled_tx_queue, sizeof(struct oled_record), 64, 1);

static void oled_tx_thread(void *a, void *b, void *c) {
    struct oled_record record;
    while (true) {
        k_msgq_get(&oled_tx_queue, &record, K_FOREVER);
        if (device_is_ready(layer_uart)) {
            for (uint8_t i = 0; i < record.length; i++) {
                uart_poll_out(layer_uart, record.bytes[i]);
            }
        }
    }
}
K_THREAD_DEFINE(oled_tx_thread_id, 512, oled_tx_thread, NULL, NULL, NULL, 10, 0, 0);

int tiny18_oled_send(uint8_t command) {
    if (command < TINY18_OLED_ACTIVITY || command > TINY18_OLED_BOOT) {
        return -EINVAL;
    }
    const struct oled_record record = {.length = 1, .bytes = {command}};
    return k_msgq_put(&oled_tx_queue, &record, K_NO_WAIT);
}

static uint8_t side_mods(zmk_mod_flags_t mods, bool right) {
    if (right) {
        return ((mods & MOD_RCTL) ? TINY18_MOD_CTRL : 0) |
               ((mods & MOD_RSFT) ? TINY18_MOD_SHIFT : 0) |
               ((mods & MOD_RALT) ? TINY18_MOD_ALT : 0) |
               ((mods & MOD_RGUI) ? TINY18_MOD_GUI : 0);
    }
    return ((mods & MOD_LCTL) ? TINY18_MOD_CTRL : 0) |
           ((mods & MOD_LSFT) ? TINY18_MOD_SHIFT : 0) |
           ((mods & MOD_LALT) ? TINY18_MOD_ALT : 0) |
           ((mods & MOD_LGUI) ? TINY18_MOD_GUI : 0);
}

static struct oled_record current_state(void) {
    const zmk_mod_flags_t mods = zmk_hid_get_explicit_mods();
    const uint8_t layer = zmk_keymap_highest_layer_active();
    return (struct oled_record){
        .length = 3,
        .bytes = {TINY18_STATE_HEADER | layer,
                  TINY18_STATE_LEFT | side_mods(mods, false),
                  TINY18_STATE_RIGHT | side_mods(mods, true)},
    };
}

static void send_state(struct k_work *work) {
    const struct oled_record state = current_state();
    k_msgq_put(&oled_tx_queue, &state, K_NO_WAIT);
}

K_WORK_DEFINE(send_state_work, send_state);

static bool is_modifier(const struct zmk_keycode_state_changed *key) {
    return key->usage_page == HID_USAGE_KEY &&
           key->keycode >= HID_USAGE_KEY_KEYBOARD_LEFTCONTROL &&
           key->keycode <= HID_USAGE_KEY_KEYBOARD_RIGHT_GUI;
}

static int layer_uart_listener(const zmk_event_t *eh) {
    const struct zmk_position_state_changed *position = as_zmk_position_state_changed(eh);
    const struct zmk_keycode_state_changed *keycode = as_zmk_keycode_state_changed(eh);

    /* Releases of ordinary keys carry nothing new; modifier releases do. */
    if (position != NULL && !position->state) {
        return ZMK_EV_EVENT_BUBBLE;
    }
    if (keycode != NULL && !is_modifier(keycode)) {
        if (keycode->state) {
            tiny18_oled_send(TINY18_OLED_ACTIVITY);
        }
        return ZMK_EV_EVENT_BUBBLE;
    }

    if (position != NULL && position->state) {
        /* A combo using these positions must not send an OLED action. */
        const bool oled_key = zmk_keymap_highest_layer_active() == 1 &&
                              position->position >= 4 && position->position <= 5;
        if (!oled_key) {
            tiny18_oled_send(TINY18_OLED_ACTIVITY);
        }
    }

    k_work_submit(&send_state_work);
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(tiny18_layer_uart, layer_uart_listener);
ZMK_SUBSCRIPTION(tiny18_layer_uart, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(tiny18_layer_uart, zmk_keycode_state_changed);
ZMK_SUBSCRIPTION(tiny18_layer_uart, zmk_position_state_changed);

static int layer_uart_init(void) {
    if (!device_is_ready(layer_uart)) {
        return -ENODEV;
    }

    tiny18_oled_send(TINY18_OLED_BOOT);
    send_state(NULL);
    return 0;
}

SYS_INIT(layer_uart_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
