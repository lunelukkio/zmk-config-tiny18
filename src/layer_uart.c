/*
 * Send Tiny18's highest active keymap layer through UART1.
 *
 * The external display is deliberately a separate USB-powered device.  A
 * single byte (0 through 7) travels from the right-half XIAO's D1 TX pin to
 * its receiver; no keyboard power or host-facing data path is involved.
 *
 * The byte goes out at boot, whenever the layer state changes, and on every
 * key press.  The last one is what lets a display plugged in later catch up:
 * the first key pressed brings it to the current layer, with no timer and no
 * request line.  Releases carry nothing new and are skipped.
 */

#include <errno.h>

#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/init.h>

#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/keymap.h>

static const struct device *const layer_uart = DEVICE_DT_GET(DT_NODELABEL(uart1));

static void send_active_layer(void) {
    const uint8_t layer = zmk_keymap_highest_layer_active();

    if (device_is_ready(layer_uart) && layer < 8) {
        uart_poll_out(layer_uart, layer);
    }
}

static int layer_uart_listener(const zmk_event_t *eh) {
    const struct zmk_position_state_changed *key = as_zmk_position_state_changed(eh);

    if (key != NULL && !key->state) {
        return ZMK_EV_EVENT_BUBBLE;
    }

    send_active_layer();
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(tiny18_layer_uart, layer_uart_listener);
ZMK_SUBSCRIPTION(tiny18_layer_uart, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(tiny18_layer_uart, zmk_position_state_changed);

static int layer_uart_init(void) {
    if (!device_is_ready(layer_uart)) {
        return -ENODEV;
    }

    send_active_layer();
    return 0;
}

SYS_INIT(layer_uart_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
