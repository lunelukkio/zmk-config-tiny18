# Only the right half selects CONFIG_TINY18_LAYER_UART. Adding the source to
# the app target (the same pattern as zmk-rgbled-widget) keeps the left half
# from creating an empty zephyr_library(), which CMake refuses to generate.
target_sources_ifdef(CONFIG_TINY18_LAYER_UART app PRIVATE src/layer_uart.c)
target_sources_ifdef(CONFIG_TINY18_START_IN_AI app PRIVATE src/start_in_ai.c)
