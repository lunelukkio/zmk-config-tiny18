# Tiny18 firmware

## English

This is a modified version of the Tiny18 firmware by 神沼三平太 (k3peta):
https://note.com/3peta/n/n44d2c364cadc

Flash `tiny18-right.uf2` to the right half and `tiny18-left.uf2` to the left
half. Use both files from this same ZIP. `settings-reset.uf2` clears saved
Bluetooth settings when recovery is needed. `tiny18_layer.bin` is for the
optional UIAPduino learning display.

`OLED-SOURCE/` contains the editable display source, the matching keymap,
and instructions for rebuilding display labels and firmware. `VERSION.txt`
records the build; `SHA256SUMS` lists file checksums.

### Install the optional learning display on Windows

These steps apply to the UIAPduino Pro Micro CH32V003 and SSD1309 display
with the wiring described in the Tiny18 display documentation. Flash both
keyboard halves with the UF2 files from this ZIP first. Other controllers or
display wiring need their own firmware and installation procedure.

1. Download the pinned [ch32fun archive](https://github.com/cnlohr/ch32fun/archive/50b6e591f466231bf3e3ea2c184b3c686e93d755.zip)
   and extract it. Keep `minichlink.exe` and `libusb-1.0.dll` together in its
   `minichlink` folder. The flasher is downloaded separately.
2. Extract this ZIP. In Windows PowerShell 5.1, enter the full paths to the
   extracted `v0.8.2` folder and `minichlink.exe` when prompted, without quotes.
3. Connect the UIAPduino directly to a PC USB port with a data cable. Hold
   reset while connecting it, then release reset immediately. Run the flash
   command. `Image written.` and `Booting` indicate that the BIN was written.

```powershell
$bundle = Read-Host 'Path to the extracted v0.8.2 folder'
Set-Location -LiteralPath $bundle
if (-not $?) { throw 'Bundle folder not found' }
$flasher = Read-Host 'Path to minichlink.exe'
if (-not (Test-Path -LiteralPath $flasher)) {
    throw 'minichlink.exe not found'
}
& $flasher -c 0x1209b803 -w .\tiny18_layer.bin flash -b
if ($LASTEXITCODE -ne 0) { throw 'OLED flash failed' }
```

To verify the written bytes, put the UIAPduino into its USB bootloader again
using the same reset procedure, then run this in the same PowerShell session:

```powershell
Set-Location -LiteralPath $bundle
if (-not $?) { throw 'Bundle folder not found' }
$readback = Join-Path $env:TEMP 'tiny18-readback.bin'
$size = (Get-Item .\tiny18_layer.bin).Length
& $flasher -c 0x1209b803 -r $readback flash $size -b
if ($LASTEXITCODE -ne 0) { throw 'OLED readback failed' }
$same = (Get-FileHash .\tiny18_layer.bin).Hash -eq
    (Get-FileHash $readback).Hash
if (-not $same) { throw 'OLED readback differs from the ZIP' }
```

Use the prebuilt `tiny18_layer.bin` above for installation. `make flash`
rebuilds the local source tree and may write a different firmware image.

Report problems at https://x.com/dendrite_lune .

### License

The original Tiny18 configuration and this project's additions use the MIT
License. The included dependencies retain their own licenses. See
`LICENSE.txt` for attribution and the full license texts. PCB manufacturing
files and case files are not included.

## 日本語

これは神沼三平太氏（k3peta）のTiny18ファームウェアを元にした改変版です。
原作の案内: https://note.com/3peta/n/n44d2c364cadc

`tiny18-right.uf2`を右手、`tiny18-left.uf2`を左手に書き込んでください。
必ずこのZIP内の同じ版を組み合わせてください。`settings-reset.uf2`は
Bluetooth設定の初期化が必要なときに使います。`tiny18_layer.bin`は
任意のUIAPduino学習用表示器向けです。

`OLED-SOURCE/`には表示器の編集用ソース、対応するキーマップ、
表示ラベルとファームウェアの再生成手順が入っています。
ビルド情報は`VERSION.txt`、ファイルのチェックサムは`SHA256SUMS`にあります。

### Windowsで学習用表示器へ書き込む

この手順は、Tiny18の表示器ドキュメントと同じ配線のUIAPduino Pro Micro
CH32V003とSSD1309 OLED向けです。先にこのZIPの左右両方のUF2を
キーボードへ書き込んでください。異なるマイコンや配線には別の対応が必要です。

1. 固定版の[ch32fun ZIP](https://github.com/cnlohr/ch32fun/archive/50b6e591f466231bf3e3ea2c184b3c686e93d755.zip)
   をダウンロードして展開します。`minichlink`フォルダー内の
   `minichlink.exe`と`libusb-1.0.dll`を同じ場所に置きます。
   書き込みツールはこの配布ZIPには入っていません。
2. このZIPを展開します。Windows PowerShell 5.1で次のコマンドを実行し、
   質問には展開後の`v0.8.2`フォルダーと`minichlink.exe`のフルパスを
   引用符なしで入力します。
3. データ対応USBケーブルでUIAPduinoをPCのUSBポートへ直接つなぎます。
   resetを押しながら接続し、すぐに離してから書き込みコマンドを
   実行します。`Image written.`と`Booting`が出れば書き込みは成功です。

```powershell
$bundle = Read-Host 'Path to the extracted v0.8.2 folder'
Set-Location -LiteralPath $bundle
if (-not $?) { throw 'Bundle folder not found' }
$flasher = Read-Host 'Path to minichlink.exe'
if (-not (Test-Path -LiteralPath $flasher)) {
    throw 'minichlink.exe not found'
}
& $flasher -c 0x1209b803 -w .\tiny18_layer.bin flash -b
if ($LASTEXITCODE -ne 0) { throw 'OLED flash failed' }
```

書き込み内容まで確認する場合は、同じ方法でもう一度USBブートローダーに入り、
同じPowerShell画面で次の読み戻しコマンドを実行してください。

```powershell
Set-Location -LiteralPath $bundle
if (-not $?) { throw 'Bundle folder not found' }
$readback = Join-Path $env:TEMP 'tiny18-readback.bin'
$size = (Get-Item .\tiny18_layer.bin).Length
& $flasher -c 0x1209b803 -r $readback flash $size -b
if ($LASTEXITCODE -ne 0) { throw 'OLED readback failed' }
$same = (Get-FileHash .\tiny18_layer.bin).Hash -eq
    (Get-FileHash $readback).Hash
if (-not $same) { throw 'OLED readback differs from the ZIP' }
```

`OLED readback differs from the ZIP`が出なければ配布BINと一致しています。
書き込みに使うのはこのZIPの`tiny18_layer.bin`です。`make flash`は
別のソースからBINを再生成するため、配布版の書き込みには使いません。

不具合の報告先: https://x.com/dendrite_lune

### ライセンス

元のTiny18設定とこのプロジェクトの追加部分はMIT Licenseです。
同梱する依存ソフトウェアにはそれぞれのライセンスが適用されます。
権利表示とライセンス全文は`LICENSE.txt`をご覧ください。
基板の製造データとケースのデータは同梱していません。
