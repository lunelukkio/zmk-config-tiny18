/*
 * Start the central half in Tiny18's AI mode.
 *
 * Layer 0 remains ZMK's always-active default layer. Activating layer 2 keeps
 * all existing layer numbers and switching combos intact while making AI the
 * highest active layer after power-on, reset, and deep-sleep wake.
 */

#include <zephyr/init.h>

#include <zmk/keymap.h>

#define TINY18_AI_LAYER 2

/* ZMK initializes the keymap at the default application priority (90). */
#define TINY18_START_LAYER_INIT_PRIORITY 91

static int tiny18_start_in_ai(void) { return zmk_keymap_layer_to(TINY18_AI_LAYER); }

SYS_INIT(tiny18_start_in_ai, APPLICATION, TINY18_START_LAYER_INIT_PRIORITY);
