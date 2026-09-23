# 任意の学習用OLED：部品・配線・導入手順

Tiny18の現在のモード、Shiftなどの修飾キー、各キーの役割を表示する、任意の外付け学習用ディスプレイです。OLEDを付けなくてもTiny18のキーボード機能はすべて使用できます。

この構成では、Tiny18右手側が現在の状態をUARTで送信し、USB給電したUIAPduinoが透明OLEDを描画します。表示器からキーボードへはデータを送り返しません。

```text
Tiny18右手側（3.3 V）
  D1 / TX ── 1 kΩ ──> RX / PD6   UIAPduino
  GND ─────────────────> GND          │
                                        │ 7本（4-wire SPI）
PCのUSBポート ── USB-C ──> 5 V給電 ────┴──> 透明OLED
```

## 必要な部品

| 数量 | 部品 | 備考 |
| ---: | --- | --- |
| 1 | [Waveshare 1.51inch Transparent OLED](https://www.waveshare.com/wiki/1.51inch_Transparent_OLED) | 128 × 64、SSD1309、ライトブルー。モジュールは既定の4-wire SPI設定で使います |
| 1 | [UIAPduino Pro Micro CH32V003 V1.4](https://www.uiap.jp/uiapduino/pro-micro/ch32v003/v1dot4) | 5 V設定で使用します。電圧選択の状態を確認してください |
| 1 | 1 kΩ抵抗 | Tiny18のD1とUIAPduinoのRXの間へ直列に入れます |
| 9本程度 | 配線材 | OLED用7本、Tiny18との通信用2本。実装方法に応じてピンヘッダーなども用意します |
| 1 | USB-Cデータケーブル | UIAPduinoの給電とファームウェア書き込みに使います |

Waveshareの公式仕様では、このOLEDモジュールは3.3 Vまたは5 Vで動作します。この手順は、UIAPduinoを5 V設定にして実機確認した構成です。基板の電圧選択が5 Vになっていることを確認し、異なる設定の基板をそのまま配線しないでください。

## 配線前の注意

配線を変更するときは、Tiny18のバッテリー電源を切り、Tiny18とUIAPduinoのUSBケーブルを両方とも外してください。

- OLEDの`RST`は、UIAPduinoの`4`へ接続します。UIAPduino本体の`RST`端子へは接続しません。
- Tiny18とUIAPduinoの間は`D1`と`GND`だけを接続します。両者の`5V`または`3V3`を接続してはいけません。
- UIAPduinoとOLEDの間は、この手順どおり7本すべてを接続します。
- OLEDモジュールは既定の4-wire SPI設定のまま使います。I2C設定へ変更しません。
- 端子の向きを外観だけで判断せず、基板に印刷された名前を確認してください。

## 1. UIAPduinoとOLEDを接続する

| OLEDの端子 | UIAPduino基板の印字 | CH32V003の端子 | 役割 |
| --- | --- | --- | --- |
| `VCC` | `5V` | 電源 | OLEDへの5 V給電 |
| `GND` | `GND` | GND | 共通GND |
| `DIN` | `8` / `MOSI` | PC6 | SPI MOSI |
| `CLK` | `7` / `SCK` | PC5 | SPI SCK |
| `CS` | `5` | PC3 | SPI chip select |
| `DC` | `6` / `A2` | PC4 | data / command |
| `RST` | `4` | PC2 | OLED reset |

UIAPduinoには`7` / `SCK`や`8` / `MOSI`が複数の場所に出ています。同じ信号名の端子は電気的に同じなので、配線しやすい側を1か所だけ使います。

## 2. Tiny18右手側とUIAPduinoを接続する

| Tiny18右手側 | 間に入れるもの | UIAPduino基板の印字 | 役割 |
| --- | --- | --- | --- |
| XIAOの`D1`（P0.03、UART TX） | 1 kΩ抵抗 | `RX`（PD6） | 9600 baud、8N1の一方向通信 |
| `GND` | なし | `GND` | 信号の基準 |

1 kΩ抵抗に向きはありません。D1からRXまでの配線の途中へ直列に入れます。UIAPduinoの`RX`は、Arduinoの論理番号では`16`または`A6`と表現されることがありますが、実際の配線では基板に印刷された`RX`を使ってください。

キーボード側からUIAPduinoへ送るだけなので、UIAPduinoの`TX`は接続しません。キーボードの電源もUIAPduinoから取りません。

## 3. 電源を入れる前に確認する

次の項目を1本ずつ確認します。

- OLEDの`RST`がUIAPduinoの`4`へ接続されている。
- OLEDの`DIN`、`CLK`、`CS`、`DC`が表の端子と一致している。
- Tiny18のD1からUIAPduinoのRXまでの途中に1 kΩ抵抗がある。
- Tiny18とUIAPduinoのGNDが接続されている。
- Tiny18とUIAPduinoの間に5 Vまたは3.3 Vの配線がない。
- 導線のほつれや、隣の端子との短絡がない。

## 4. ファームウェアを書き込む

キーボード左右のUF2と、表示器の`tiny18_layer.bin`は、同じキーマップから作られた同じバージョンを使用してください。異なる版を組み合わせると、OLEDの表示と実際のキー動作が一致しないことがあります。

`tiny18_layer.bin`を含む公開Releaseでは、同じバージョンの次の3ファイルを組み合わせて使います。

- `tiny18-right.uf2`：Tiny18右手側
- `tiny18-left.uf2`：Tiny18左手側
- `tiny18_layer.bin`：UIAPduino

受信側ソースは、このリポジトリの[`addons/oled/`](../addons/oled/)に含まれています。
Windows PowerShell 5.1で、固定版のch32funと書き込みツールも取得します。
以下ではホーム直下へcloneした例を使います。すでにcloneしている場合は、
その場所で`git submodule update --init --recursive`を実行してください。

```powershell
Set-Location ~; git clone --recurse-submodules https://github.com/lunelukkio/zmk-config-tiny18.git
```

公開済みの統合ZIPを使う場合は、`firmware/vX.Y.Z/`に展開してください。
左右のUF2とOLEDのBINを同じZIPから選びます。この方法ではコンパイラは不要です。

ソースから作る場合だけ、[OLEDのビルド環境](../addons/oled/README.md)を準備し、
機器を接続する前にビルドします。`make`だけでは書き込みません。

```powershell
Set-Location ~\zmk-config-tiny18\addons\oled; make OS=Windows_NT PREFIX=riscv-none-elf tiny18_layer.bin
```

UIAPduinoを書き込むときは、次の順序にします。

1. Tiny18のバッテリー電源を切ります。
2. UIAPduinoをいったんUSBから外し、データケーブルを用意します。USBハブは使いません。
3. UIAPduinoのresetを押したまま、PC本体のUSBポートへ直接接続し、接続直後にresetを離します。
4. ソースからビルドした場合は、すぐに次のコマンドを実行します。

```powershell
Set-Location ~\zmk-config-tiny18\addons\oled; make OS=Windows_NT PREFIX=riscv-none-elf flash
```

公開ZIPのBINを書き込む場合は、手順4の代わりに次を実行します。
`v0.3.1`は記入例で、実際に取得したバージョン番号へ置き換えてください。

```powershell
Set-Location ~\zmk-config-tiny18\addons\oled; .\ch32fun\minichlink\minichlink.exe -c 0x1209b803 -w ..\..\firmware\v0.3.1\tiny18_layer.bin flash -b
```

出力に`Image written.`と`Booting`が表示されれば書き込み成功です。bootloaderを何度も認識できない場合は、USBハブ、充電専用ケーブル、resetを離すタイミングを先に確認してください。

## 5. 動作を確認する

1. UIAPduinoをUSB給電します。
2. OLEDが約0.5秒白く点灯し、その後AIモードのキー配置になることを確認します。
3. Tiny18左右の電源を入れ、右手側を起動します。
4. モード切替comboを押し、OLEDの表示も同じモードへ変わることを確認します。
5. Shift、Ctrl、Alt、GUIを押さえ、該当する表示へ変わることを確認します。

Tiny18は30分操作しないとdeep sleepへ入り、OLEDも有効な状態を30分受信しないと消灯します。復帰時はTiny18右手側のキーを1回押してキーボードを起こします。この1打鍵は文字として入力されません。次の有効な状態を受信するとOLEDも再点灯します。

## 困ったとき

| 症状 | 確認すること |
| --- | --- |
| OLEDがまったく点灯しない | `VCC`、`GND`、USB給電、OLEDの4-wire SPI設定を確認します |
| 白く点灯するが画面が変わらない | `DIN`、`CLK`、`CS`、`DC`、OLEDの`RST`からUIAPduinoの`4`への配線を確認します |
| AI画面は出るがTiny18と同期しない | Tiny18のD1、1 kΩ抵抗、UIAPduinoの`RX`、両者のGNDを確認します |
| 表示内容だけが実際のキーと違う | 左右UF2と`tiny18_layer.bin`が同じバージョンか確認します。ZMK Studioで変更した配列はOLEDへ自動転送されません |
| `make flash`が機器を見つけない | PC本体へ直結したデータケーブルか確認し、resetを押したまま接続して直後に離します |

## 公式資料

- [Waveshare 1.51inch Transparent OLED Wiki](https://www.waveshare.com/wiki/1.51inch_Transparent_OLED)
- [UIAPduino Pro Micro CH32V003 V1.4](https://www.uiap.jp/uiapduino/pro-micro/ch32v003/v1dot4)
- [UIAPduino Pro Micro CH32V003 V1.4 schematic](https://www.uiap.jp/doc/UIAPduino-Pro-Micro-CH32V003-V1dot4-sch.pdf)
