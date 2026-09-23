#!/usr/bin/env bash
# Run inside the same SDK container as the ZMK v0.3.0 Actions workflow.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
workspace=${1:?Usage: build-keyboard.sh /absolute/build-workspace}
case "$workspace" in
  /*) ;;
  *) echo "The build workspace must be absolute." >&2; exit 2 ;;
esac
mkdir -p "$workspace"
workspace=$(cd "$workspace" && pwd)
if [[ "$workspace" == "$repo" || "$workspace" == / ]]; then
  echo "Use a separate build workspace, not the source root." >&2
  exit 2
fi
mkdir -p "$workspace/config" "$workspace/firmware"
cp -R "$repo/config/." "$workspace/config/"
cd "$workspace"
if [[ ! -d .west ]]; then
  west init -l config
fi
west update --fetch-opt=--filter=tree:0
west zephyr-export
west manifest --freeze --active-only > resolved-west.yml

# Keep these three invocations in sync with build.yaml. The module path is
# independent of the west manifest directory, just as in the upstream workflow.
west build -s zmk/app -d right -b seeeduino_xiao_ble \
  -S studio-rpc-usb-uart -- \
  -DZMK_CONFIG="$workspace/config" -DZMK_EXTRA_MODULES="$repo" \
  -DSHIELD="tiny18_r rgbled_adapter" -DCONFIG_ZMK_STUDIO=y
cp right/zephyr/zmk.uf2 firmware/tiny18-right.uf2

west build -s zmk/app -d left -b seeeduino_xiao_ble -- \
  -DZMK_CONFIG="$workspace/config" -DZMK_EXTRA_MODULES="$repo" \
  -DSHIELD="tiny18_l rgbled_adapter"
cp left/zephyr/zmk.uf2 firmware/tiny18-left.uf2

west build -s zmk/app -d reset -b seeeduino_xiao_ble -- \
  -DZMK_CONFIG="$workspace/config" -DZMK_EXTRA_MODULES="$repo" \
  -DSHIELD=settings_reset
cp reset/zephyr/zmk.uf2 firmware/settings-reset.uf2
printf 'Built all three keyboard images in %s/firmware\n' "$workspace"
