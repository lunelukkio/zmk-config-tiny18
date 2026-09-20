# Tiny18 ZMK firmware (lunelukkio's fork)

[![Build](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml/badge.svg)](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml)
[![Latest release](https://img.shields.io/github/v/release/lunelukkio/zmk-config-tiny18?display_name=tag)](https://github.com/lunelukkio/zmk-config-tiny18/releases/latest)

ZMK firmware for [Tiny18](https://github.com/k3peta/tiny18), an 18-key wireless split keyboard using two Seeed Studio XIAO nRF52840 controllers. Tiny18, its PCB and its stock firmware are by k3peta. This fork of [k3peta/zmk-config-tiny18](https://github.com/k3peta/zmk-config-tiny18) carries one person's keymap, plus a small module that reports the active layer to an external learning display.

日本語の説明は [`README.ja.md`](README.ja.md) を参照してください。

## What differs from upstream

- **Keymap.** Six modes and two held pages across eight layers, with 24 combos. The right hand rests on a trackball, so everything used daily fits on the left nine keys. The full layout, with diagrams and the reasoning, is at [lunelukkio.com/public/tiny18/keymap.html](https://lunelukkio.com/public/tiny18/keymap.html).
- **One right-hand image.** `tiny18-right.uf2` has inverted-T arrows in AI mode. W sends Escape, or Tab with Shift; R sends BackSpace, or Delete with Shift. The right top row sends Ctrl+Z, Ctrl+Shift+Z and Ctrl+X. Holding Shift turns the six right-hand keys into `/model`, `/resume`, `/status`, `/clear`, `/context` and `/permissions`.
- **AI at startup.** Power-on, reset and wake from deep sleep all start in AI mode. The right-half RGB LED starts blue, and the text-entry combo remains available when typing is needed.
- **Layer colours.** The right half's RGB LED shows the mode: green for text entry, blue for AI, yellow for the number keypad, cyan for game, magenta for function, red for Bluetooth, and white while a held page is open.
- **Deep sleep.** Both halves sleep after 30 minutes idle (`CONFIG_ZMK_SLEEP=y`, `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=1800000`). Waking takes a key press on the right half, and that press is lost.
- **Learning display.** [`src/layer_uart.c`](src/layer_uart.c) sends one byte over UART1 (D1, TX only, 9600 baud, 8N1) at boot, whenever the layer or a held modifier changes, and on every key press: the highest active layer in bits 0 to 2, then Shift, Ctrl, Alt and GUI in bits 3 to 6. A USB-powered CH32V003 board draws the current key labels on a transparent OLED; its firmware lives in [lunelukkio/t-display](https://github.com/lunelukkio/t-display). The right half enables it with `CONFIG_TINY18_LAYER_UART=y`.

## Keymap

The canonical keymap is [`config/tiny18.keymap`](config/tiny18.keymap); the comments in it explain each decision. [`build.yaml`](build.yaml) builds one image per half. GitHub Actions redraws [`keymap-drawer/tiny18.svg`](keymap-drawer/tiny18.svg) whenever a push touches the firmware files.

![Tiny18 keymap](keymap-drawer/tiny18.svg)

| Mode | Layer | Switch | What it is for |
| --- | --- | --- | --- |
| Text entry | 0 | `W + R` | Letters |
| AI | 2 | `S + F` | The mode at power-on; inverted-T arrows, Escape/Tab, BackSpace/Delete, undo/redo/cut on the right top row, six slash commands while Shift is held, punctuation on the right, and copy and paste chords |
| Number keypad | 3 | `J + L` | Keypad digits, which pass through an IME as half width |
| Game | 5 | `R + S` | WASD for VRChat, with R I O P and chat keys |
| Function | 4 | `U + O` | F1 to F12 |
| Bluetooth | 1 | `O + J` | Profile selection |

Each mode is entered by one two-key combo; AI and game mode entry are disabled within game mode. The switching combos fire only after 150 ms without typing. Two more layers open only while a thumb is held: the digit and symbol page on BackSpace, the ZXCV page on Space or N. They are layers 6 and 7, the two highest, and open from modes that retain the text-entry thumbs.

Keys are named by what they type in text entry:

- In text entry, `A` is a plain key and repeats while held. `Enter` is a hold-tap there and in every mode and page: tap for Enter, hold for Shift. AI mode and the digit page also give the `A` position that Enter / Shift role, with a 350 ms term for the left little finger; game mode keeps a plain Shift there.
- `BackSpace` opens the digit page while held, `Space` and `N` open the ZXCV page, and `M` holds Ctrl. The two left thumbs retain those roles outside number and game modes.
- `E + F` pressed together toggles the IME (Ctrl+Space) in text entry, once 150 ms have passed without typing. The six slash-command macros in AI mode send the HID `LANG2` key, which Windows takes as IME off and macOS as Eisu, so they arrive as ASCII whatever the IME was doing.
- Letters without a key of their own come from adjacent pairs: `Q T Y P G H` in text entry and `B` on the ZXCV page. `A` has both a key and a pair.
- Alt is `R + F` and GUI is `U + J`, in text entry and AI mode.

## Download

UF2 files for tagged versions are on the [Releases](https://github.com/lunelukkio/zmk-config-tiny18/releases) page and do not expire. `main` may be ahead of the latest release; the `firmware` artifact of the latest [build run](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml) has the current images, and expires.

| File | Target |
| --- | --- |
| `tiny18-right.uf2` | Right half, AI-mode arrows in the usual inverted T; Bluetooth central, ZMK Studio host, learning display sender |
| `tiny18-left.uf2` | Left half; Bluetooth peripheral |
| `settings-reset.uf2` | Clears stored Bluetooth and split settings |
| `SHA256SUMS` | SHA-256 checksums for the three UF2 files |

The right and left files are not interchangeable. If the wrong image is flashed, enter the bootloader again and flash the correct image. Only the right half interprets the keymap. Flash the right and left images from the same build together.

## Flashing

1. Turn the keyboard's battery power switch off and connect one half with a USB data cable.
2. Double-press the XIAO reset button. A drive named `XIAO-SENSE` should appear.
3. Copy `tiny18-right.uf2` to the right half and `tiny18-left.uf2` to the left half.
4. Disconnect USB, turn both halves on, and pair the Bluetooth device named `tiny18`.

For a first installation, or if the halves or host no longer pair correctly:

1. Flash `settings-reset.uf2` to both halves.
2. Double-press reset again on each half.
3. Flash the matching right and left firmware.
4. Remove any old `tiny18` entry from the host's Bluetooth settings, then pair again.

ZMK Studio is enabled on the right half. A keymap edited in Studio is stored in the settings partition and takes precedence over the compiled one, so if a freshly flashed keymap does not show up, flash `settings-reset.uf2` first.

## Build from source

GitHub Actions builds the three images automatically when firmware-related files change. The build is pinned to ZMK `v0.3.0` and `zmk-rgbled-widget` `v0.3.0` so a given commit remains reproducible.

To build a fork:

1. Fork this repository.
2. Enable GitHub Actions in the fork.
3. Edit `config/tiny18.keymap` if you want a custom layout.
4. Push the change and download the `firmware` artifact from the completed workflow run.

Actions artifacts are intended for testing and expire. Permanent downloads come from pushing a version tag such as `v3.1.0`; [`release.yml`](.github/workflows/release.yml) builds that exact tag, creates checksums, and attaches the UF2 files to a GitHub Release.

### Build matrix

[`build.yaml`](build.yaml) produces:

- right half with RGB LED layer/battery widget, ZMK Studio over USB and the layer UART
- left half with RGB LED layer/battery widget
- settings-reset image for recovery

## Repository structure

| Path | Purpose |
| --- | --- |
| `config/tiny18.keymap` | Canonical keymap |
| `config/tiny18_*.conf` | Per-half ZMK configuration: LED colours, deep sleep, and on the right half ZMK Studio and the layer UART |
| `boards/shields/tiny18/` | Tiny18 shield and direct-pin hardware definition; the right overlay adds UART1 on D1 |
| `src/layer_uart.c`, `src/start_in_ai.c`, `Kconfig`, `CMakeLists.txt`, `zephyr/module.yml` | The learning display sender and AI-mode startup, built as a Zephyr module of this repository |
| `build.yaml` | Firmware build matrix and stable artifact names |
| `keymap-drawer/` | Generated keymap diagram |
| `.github/workflows/build.yml` | Continuous build and diagram generation |
| `.github/workflows/release.yml` | Permanent, tagged firmware releases |

## Hardware

PCB production files, BOM, and fabrication notes are in the [Tiny18 hardware repository](https://github.com/k3peta/tiny18). This repository carries no hardware files.

## License

Tiny18-specific firmware configuration and shield files are licensed under the [MIT License](LICENSE); the copyright notice in that file is the upstream author's and stays with the fork. ZMK and external modules are separate projects and retain their respective licenses.
