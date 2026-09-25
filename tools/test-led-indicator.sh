#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
binary=/tmp/tiny18-led-indicator-state-test
trap 'rm -f "$binary"' EXIT

cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -I"$repo/src" \
  "$repo/src/led_indicator_state.c" \
  "$repo/tests/led_indicator_state_test.c" \
  -o "$binary"

"$binary"
