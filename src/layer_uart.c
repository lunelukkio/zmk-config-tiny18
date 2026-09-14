/*
 * Send Tiny18's display state through UART1.
 *
 * The external display is deliberately a separate USB-powered device.  A
 * single byte travels from the right-half XIAO's D1 TX pin to its receiver;
 * no keyboard power or host-facing data path is involved.
 *
 * The byte carries the highest active keymap layer in bits 0-2 and one bit
 * each for Shift, Ctrl, Alt and GUI in bits 3-6, whichever side is held.
 * Bit 7 stays clear so the receiver can tell a byte from line noise.
 *
 * It goes out at boot, whenever the layer state changes, whenever a modifier
 * key goes down or up, and on every key press.  The last one is what lets a
 * display plugged in later catch up: the first key pressed brings it to the
 * current state, with no timer and no request line.
 *
 * The listeners do not send directly.  They queue one work item, and the
 * work reads the state and writes the byte.  Two reasons: this file's
 * listener can run before ZMK's own HID listener for the same event, so the
 * modifier state is only current once the event has finished its round; and
 * uart_poll_out blocks for about a millisecond per byte, which does not
 * belong in the event path.  Several events from one keystroke collapse into
 * a single byte this way.
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

#define STATE_SHIFT 0x08
#define STATE_CTRL 0x10
#define STATE_ALT 0x20
#define STATE_GUI 0x40

static const struct device *const layer_uart = DEVICE_DT_GET(DT_NODELABEL(uart1));

static uint8_t current_state(void) {
    const zmk_mod_flags_t mods = zmk_hid_get_explicit_mods();
    uint8_t state = zmk_keymap_highest_layer_active() & 0x07;

    if (mods & (MOD_LSFT | MOD_RSFT)) {
        state |= STATE_SHIFT;
    }
    if (mods & (MOD_LCTL | MOD_RCTL)) {
        state |= STATE_CTRL;
    }
    if (mods & (MOD_LALT | MOD_RALT)) {
        state |= STATE_ALT;
    }
    if (mods & (MOD_LGUI | MOD_RGUI)) {
        state |= STATE_GUI;
    }
    return state;
}

static void send_state(struct k_work *work) {
    if (device_is_ready(layer_uart)) {
        uart_poll_out(layer_uart, current_state());
    }
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
        return ZMK_EV_EVENT_BUBBLE;
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

    send_state(NULL);
    return 0;
}

SYS_INIT(layer_uart_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
