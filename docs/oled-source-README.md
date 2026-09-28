# Tiny18 OLED source / 表示器のソース

## English

This folder contains the editable source for the optional Tiny18 learning
display. The matching prebuilt firmware is `../tiny18_layer.bin`.

Edit `config/tiny18.keymap` to change displayed key labels. The build helper
generates `addons/oled/layers.h` from that keymap and builds
`addons/oled/tiny18_layer.bin`. You can also edit the display code in
`addons/oled/`. Regeneration replaces `layers.h`.

Install Python, [uv](https://docs.astral.sh/uv/), Git, GNU Make, and the
[xPack RISC-V Embedded GCC toolchain](https://xpack-dev-tools.github.io/riscv-none-elf-gcc-xpack/docs/install/).
The tested compiler version is 14.2.0-3. In Windows PowerShell 5.1, first
change to the extracted `OLED-SOURCE` folder, then run:

```powershell
Set-Location .\OLED-SOURCE
uv run --no-project --with pillow python build_oled.py
```

The helper fetches ch32fun at pinned commit
`50b6e591f466231bf3e3ea2c184b3c686e93d755` to keep this ZIP small.
It builds the BIN but does not flash the device. Changing keyboard behavior
requires building new firmware for both keyboard halves from the full project.

Report problems at https://x.com/dendrite_lune . Software licenses and
attribution are in `../LICENSE.txt`.

## 日本語

このフォルダーには、任意のTiny18学習用表示器の編集用ソースが入っています。
対応する書き込み済みファイルは`../tiny18_layer.bin`です。

表示するキー名は`config/tiny18.keymap`を編集してください。
`build_oled.py`がキーマップから`addons/oled/layers.h`を生成し、
`addons/oled/tiny18_layer.bin`をビルドします。表示処理は`addons/oled/`の
ソースでも変更できます。`layers.h`の直接編集は再生成時に上書きされます。

Python、uv、Git、GNU Make、xPack RISC-V Embedded GCCを用意してください。
確認済みのコンパイラーは14.2.0-3です。Windows PowerShell 5.1で
展開した`OLED-SOURCE`フォルダーへ移動し、上のコマンドを実行します。

ビルド時に固定版ch32funを取得します。BINは生成されますが、
マイコンへの書き込みは行いません。キーボード自体の動作を変える場合は、
プロジェクト全体のソースから左右両方のファームウェアを作り直してください。

不具合の報告先: https://x.com/dendrite_lune
ライセンスと権利表示は`../LICENSE.txt`をご覧ください。
