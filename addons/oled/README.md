# Optional Tiny18 OLED receiver

This component is not required to use or build the keyboard. It targets the
UIAPduino Pro Micro CH32V003 V1.4 and Waveshare 1.51inch Transparent OLED.
See the [Japanese parts, wiring and flashing guide](../../docs/oled-setup.md).

## Source and dependency

- `tiny18_layer.c`: UART receiver, OLED SPI driver and idle/wake behavior.
- `render.c`, `render.h`: labels and modifier indicators.
- `layers.h`: generated from `config/tiny18.keymap`; do not edit by hand.
- `funconfig.h`, `Makefile`: CH32V003 build configuration.
- `ch32fun/`: public submodule pinned to
  `50b6e591f466231bf3e3ea2c184b3c686e93d755`. Initialize it at the parent
  repository root with `git submodule update --init --recursive`.

The receiver/renderer is covered by the root [MIT license](../../LICENSE).
ch32fun retains its [own license](ch32fun/LICENSE), embedded source notices,
and [runtime library terms](ch32fun/misc/LIBGCC_LICENSE).

## Windows build

Install Git, GNU Make, and an RV32E-capable RISC-V toolchain. The verified
Windows build uses xPack RISC-V Embedded GCC **14.2.0-3**, with
`make.exe`, `riscv-none-elf-gcc.exe` and binutils on PATH. Follow the
[xPack installation instructions](https://xpack-dev-tools.github.io/riscv-none-elf-gcc-xpack/docs/install/).
The commands below assume a clone at `~/zmk-config-tiny18`.

```powershell
Set-Location ~\zmk-config-tiny18; git submodule update --init --recursive
Set-Location ~\zmk-config-tiny18; uv run --no-project --with pillow python docs/tools/make_oled_layers.py
Set-Location ~\zmk-config-tiny18\addons\oled; make OS=Windows_NT PREFIX=riscv-none-elf tiny18_layer.bin
```

The result is `tiny18_layer.bin`. Plain `make` builds only; it never flashes.
After connecting the board in bootloader mode, use `make flash` as described
in the setup guide. The bootloader is selected explicitly as USB `1209:b803`.
The pinned submodule includes the Windows `minichlink.exe` and companion DLLs;
they are not installed globally by this project.

## Linux build / CI

Use GNU Make, `gcc-riscv64-unknown-elf`, and `libnewlib-dev` (Ubuntu packages).
The last package supplies the C headers used by ch32fun, not a linked libc.
`.github/workflows/oled.yml` builds the `tiny18_layer.bin` Make target with
`PREFIX=riscv64-unknown-elf` on Ubuntu. Flashing on Linux also
requires the host-side minichlink dependencies described in
[ch32fun's README](ch32fun/README.md); building a BIN alone does not.

## Changing the layout

Change `config/tiny18.keymap`, then regenerate the chart, HTML and OLED header
using the [build guide](../../docs/build-and-release.md). Flash both keyboard
halves and the OLED from the same version. Studio edits do not rewrite this
receiver's compiled-in labels. No old display project or website checkout is
needed for any of these steps.
