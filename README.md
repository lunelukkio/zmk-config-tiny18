# Tiny18 ZMK firmware (lunelukkio's fork)

[![Build](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml/badge.svg)](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml)
[![Latest release](https://img.shields.io/github/v/release/lunelukkio/zmk-config-tiny18?display_name=tag)](https://github.com/lunelukkio/zmk-config-tiny18/releases/latest)

ZMK firmware for [Tiny18](https://github.com/k3peta/tiny18), an 18-key wireless split keyboard using two Seeed Studio XIAO nRF52840 controllers. Tiny18, its PCB and its stock firmware are by k3peta. This fork of [k3peta/zmk-config-tiny18](https://github.com/k3peta/zmk-config-tiny18) carries one person's keymap, plus a small module that reports the active layer to an external learning display.

日本語の説明は [`README.ja.md`](README.ja.md) を参照してください。

## Choose your setup

- **Keyboard only:** use the right and left UF2 files. No OLED, RISC-V compiler,
  or submodule checkout is required.
- **Optional OLED:** the receiver source is included in [`addons/oled/`](addons/oled/).
  Follow the [parts and wiring guide](docs/oled-setup.md) and use the matching
  `tiny18_layer.bin`. There is no separate private repository to obtain.
- [Build and release guide](docs/build-and-release.md) ·
  [Full keymap chart](docs/tiny18-keymap.png) · [Offline keymap page](docs/keymap.html)

## What differs from upstream

- **Keymap.** Six modes and two held pages across eight layers, with 28 combos. The right hand rests on a trackball, so everything used daily fits on the left nine keys. The full layout, with diagrams and the reasoning, is at [lunelukkio.com/public/tiny18/keymap.html](https://lunelukkio.com/public/tiny18/keymap.html).
- **One right-hand image.** `tiny18-right.uf2` has inverted-T arrows under both hands in AI mode. W sends Escape, or Tab with Shift; R sends BackSpace, or Delete with Shift. The right top row is period, up arrow and slash. Neighbouring right-hand pairs chord Ctrl+Z, Ctrl+Shift+Z, Ctrl+X and Ctrl+F. Holding Shift turns the period and slash into `/model` and `/status`; the four arrows stay plain arrows under Shift, so Shift+arrow selects with either hand.
- **AI at startup.** Power-on, reset and wake from deep sleep all start in AI mode. The right-half RGB LED starts blue, and the text-entry combo remains available when typing is needed.
- **Layer colours.** The right half's RGB LED shows the mode: green for text entry, blue for AI, yellow for the number keypad, cyan for game, magenta for function, red for Bluetooth, and white while a held page is open.
- **Deep sleep.** Both halves sleep after 30 minutes idle (`CONFIG_ZMK_SLEEP=y`, `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=1800000`). Waking takes a key press on the right half, and that press is lost.
- **Learning display.** [`src/layer_uart.c`](src/layer_uart.c) sends one byte over UART1 (D1, TX only, 9600 baud, 8N1) at boot, whenever the layer or a held modifier changes, and on every key press: the highest active layer in bits 0 to 2, then Shift, Ctrl, Alt and GUI in bits 3 to 6. A USB-powered CH32V003 board draws the current key labels on a transparent OLED; its firmware is included in [`addons/oled/`](addons/oled/). See the [Japanese parts, wiring and setup guide](docs/oled-setup.md) for the tested hardware and exact connections. The right half enables it with `CONFIG_TINY18_LAYER_UART=y`.

## Keymap

The canonical keymap is [`config/tiny18.keymap`](config/tiny18.keymap); the comments in it explain each decision. [`build.yaml`](build.yaml) builds one image per half. GitHub Actions redraws [`keymap-drawer/tiny18.svg`](keymap-drawer/tiny18.svg) whenever a push touches the firmware files.

![Tiny18 keymap](keymap-drawer/tiny18.svg)

| Mode | Layer | Switch | What it is for |
| --- | --- | --- | --- |
| AI | 2 | `S + F` | The mode at power-on; inverted-T arrows on both hands, Escape/Tab, BackSpace/Delete, `/model` and `/status` while Shift is held, punctuation on the right, copy and paste chords on the left, and undo/redo/cut/find chords on the right |
| Text entry | 0 | `W + R` | Letters |
| Number keypad | 3 | `J + L` | Keypad digits, which pass through an IME as half width |
| Game | 5 | `R + S` | WASD for VRChat, with R I O P and chat keys |
| Function | 4 | `U + O` | F1 to F12 |
| Bluetooth | 1 | `O + J` | Profile selection |

Each mode is entered by one two-key combo; AI and game mode entry are disabled within game mode. The switching combos fire only after 150 ms without typing. Two more layers open only while a thumb is held: the digit and symbol page on BackSpace, the ZXCV page on Space or N. They are layers 6 and 7, the two highest, and open from modes that retain the text-entry thumbs.

Keys are named by what they type in text entry:

- In text entry, `A` taps A and holds Shift after 350 ms. A quick tap followed by holding it again keeps A held for the host's auto-repeat. `Enter` is a hold-tap there and in every mode and page: tap for Enter, hold for Shift. AI mode and the digit page give the `A` position that Enter / Shift role with the same 350 ms term; game mode keeps a plain Shift there.
- `BackSpace` opens the digit page while held, `Space` and `N` open the ZXCV page, and `M` holds Ctrl. The two left thumbs retain those roles outside number and game modes.
- `E + F` pressed together toggles the IME (Ctrl+Space) in text entry, once 150 ms have passed without typing. The two slash-command macros in AI mode send the HID `LANG2` key, which Windows takes as IME off and macOS as Eisu, so they arrive as ASCII whatever the IME was doing.
- Letters without a key of their own come from adjacent pairs: `Q T Y P G H` in text entry and `B` on the ZXCV page. `A` has both a key and a pair.
- Alt is `R + F` and GUI is `U + J`, in text entry and AI mode.

## Download

For installation or redistribution, use a versioned integrated ZIP that includes
`LICENSES/`. Earlier [Releases](https://github.com/lunelukkio/zmk-config-tiny18/releases)
may contain only UF2 files and checksums without the corresponding third-party
license material; keep those as historical recovery images and do not redistribute
the binaries by themselves. `main` may be ahead of the latest release. The
`firmware` artifact of the latest [build run](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml)
has current test images and expires, but it also lacks the complete license bundle.

| File | Target |
| --- | --- |
| `tiny18-right.uf2` | Right half, AI-mode arrows in the usual inverted T; Bluetooth central, ZMK Studio host, learning display sender |
| `tiny18-left.uf2` | Left half; Bluetooth peripheral |
| `settings-reset.uf2` | Clears stored Bluetooth and split settings |
| `tiny18_layer.bin` | Optional UIAPduino OLED receiver |
| `VERSION.txt` | Shared version, source revisions, build date and Actions run |
| `LICENSES/` | Dependency license texts and attribution inventory |
| `SHA256SUMS` | SHA-256 checksums for all bundle files |

New integrated releases contain one `tiny18-vX.Y.Z.zip`; extract it and keep
`LICENSES/` with the firmware. OLED users must use a bundle containing all three
device images.

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

GitHub Actions builds the three images automatically when firmware-related files change. The configuration selects ZMK `v0.3.0` and `zmk-rgbled-widget` `v0.3.0`. Integrated bundles also record the resolved dependency commits; compiler and container updates can change binary output.

To build a fork:

1. Fork this repository.
2. Enable GitHub Actions in the fork.
3. Edit `config/tiny18.keymap` if you want a custom layout.
4. Push the change and download the `firmware` artifact from the completed workflow run for personal testing.

Actions artifacts are intended for personal testing, expire, and do not contain the
complete license bundle required for redistribution. OLED builds run separately, so
their toolchain is not required for keyboard-only builds. A version tag such as
`v0.3.1` runs [`release.yml`](.github/workflows/release.yml), which builds both
components and creates an **unpublished draft** with a versioned ZIP and license
material. Publication is a separate manual step after review; see the
[build and release guide](docs/build-and-release.md).

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
| `addons/oled/` | Optional receiver, renderer and pinned ch32fun submodule |
| `docs/tools/` | Shared keymap, chart, HTML and OLED generators and tests |
| `docs/oled-setup.md` | OLED product names, wiring and installation |
| `tools/`, `tests/` | Local keyboard build, license export and bundle tooling |
| `firmware/` | Local versioned bundles (generated files are ignored) |
| `keymap-drawer/` | Generated keymap diagram |
| `.github/workflows/build.yml` | Continuous build and diagram generation |
| `.github/workflows/oled.yml` | Separate optional OLED build and generator checks |
| `.github/workflows/release.yml` | Integrated draft releases, requiring manual publication |

## Support

Please use [GitHub Issues](https://github.com/lunelukkio/zmk-config-tiny18/issues) for bug reports, setup questions, and suggestions. This project does not publish a contact email address; Issues are the normal contact channel.

## Hardware

This project distributes keyboard software and optional learning-display software, together with their source and documentation. Physical PCBs and PCB manufacturing files are not distributed here. To obtain the PCB Gerber files and case or switch-plate STL files used by this project, purchase them from the original author's paid article, [Tiny18 build manual: version 1/version 2 hardware and shared firmware](https://note.com/3peta/n/n44d2c364cadc) (Japanese). Purchased files are not included in this repository and may not be redistributed, including mirrored or modified versions.

For general hardware information and hardware resources published separately by the original author, see the [Tiny18 hardware repository](https://github.com/k3peta/tiny18). The files under `boards/shields/` are software configuration needed to build the firmware, not PCB manufacturing data.

## License

Tiny18-specific firmware configuration and shield files are licensed under the [MIT License](LICENSE). The upstream copyright notice, `Copyright (c) 2025-2026 k3peta`, is preserved. Original software additions and modifications by lunelukkio are also licensed under MIT, with `Copyright (c) 2026 lunelukkio`.

ZMK, Zephyr, and external libraries retain their own copyright notices and licenses. The MIT license for this fork does not relicense those dependencies. See [Licensing and distribution scope](docs/licensing.md) for the source references and firmware distribution requirements.

Purchased Gerber files and purchased case or switch-plate STL files, including mirrored or modified versions, have no redistribution permission and must not be included in this repository, source archives, firmware packages, or published documentation. They are outside the scope of the software license.
