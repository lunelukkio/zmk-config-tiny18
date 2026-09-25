# Only the right half selects CONFIG_TINY18_LAYER_UART. Adding the source to
# the app target (the same pattern as zmk-rgbled-widget) keeps the left half
# from creating an empty zephyr_library(), which CMake refuses to generate.
target_include_directories(app PRIVATE include)
target_sources_ifdef(CONFIG_TINY18_LAYER_UART app PRIVATE src/layer_uart.c)
target_sources_ifdef(CONFIG_ZMK_BEHAVIOR_TINY18_OLED_CONTROL app PRIVATE src/behavior_oled_control.c)
target_sources_ifdef(CONFIG_TINY18_START_IN_AI app PRIVATE src/start_in_ai.c)
target_sources_ifdef(CONFIG_TINY18_LED_INDICATOR app PRIVATE
  src/led_indicator.c
  src/led_indicator_state.c
)
target_sources_ifdef(CONFIG_ZMK_BEHAVIOR_TINY18_LED_MODE app PRIVATE
  src/behavior_led_mode.c
)
target_sources_ifdef(CONFIG_ZMK_BEHAVIOR_TINY18_LED_BRIGHTNESS app PRIVATE
  src/behavior_led_brightness.c
)
