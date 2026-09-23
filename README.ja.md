# Tiny18 ZMK ファームウェア（lunelukkio の fork）

[![Build](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml/badge.svg)](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml)
[![Latest release](https://img.shields.io/github/v/release/lunelukkio/zmk-config-tiny18?display_name=tag)](https://github.com/lunelukkio/zmk-config-tiny18/releases/latest)

Seeed Studio XIAO nRF52840 を2個使う18キー左右分割キーボード [Tiny18](https://github.com/k3peta/tiny18) 用の ZMK ファームウェアです。Tiny18 の設計、基板、元のファームウェアは k3peta さんの作です。このリポジトリは [k3peta/zmk-config-tiny18](https://github.com/k3peta/zmk-config-tiny18) の fork で、個人用のキーマップと、外付けの学習用表示器へ現在のレイヤーを送る小さなモジュールを載せています。

## 使い方を選ぶ

- **キーボードだけ使う：** 左右のUF2を書き込みます。OLED、RISC-Vコンパイラ、submoduleの取得は不要です。
- **OLEDも付ける：** 受信側ソースは同じリポジトリの[`addons/oled/`](addons/oled/)に含まれます。[部品・配線・導入手順](docs/oled-setup.md)に従い、同じ版の`tiny18_layer.bin`を使います。別の非公開リポジトリは不要です。
- [ビルド・配布手順](docs/build-and-release.md) · [全体配置図](docs/tiny18-keymap.png) · [オフラインで読める説明ページ](docs/keymap.html)

## 上流との違い

- **キーマップ。** 6つのモードと押しっぱなしで開く2つの面、全8レイヤー、combo 28個。右手はトラックボールの上に置いたままなので、日常的に使う操作は左手9キーに収めてあります。配置図と理由は [lunelukkio.com/public/tiny18/keymap.html](https://lunelukkio.com/public/tiny18/keymap.html) にまとめてあります。
- **右手の uf2 は1種類。** `tiny18-right.uf2` の AI モードは左右とも矢印が逆 T 字です。W の位置は Escape、Shift 中は Tab、R の位置は BackSpace、Shift 中は Delete です。右上段は `.`、↑、`/`。右手の隣り合う2キーの combo で `Ctrl+Z`、`Ctrl+Shift+Z`、`Ctrl+X`、`Ctrl+F` が出ます。Shift を押さえている間、両端の `.` と `/` だけが `/model` と `/status` になります。4方向の矢印はShiftを押さえても変わらないので、Shift+矢印の選択はどちらの手でもできます。
- **起動時は AI。** 電源投入、リセット、deep sleepからの復帰はいずれもAIモードから始まります。右手のRGB LEDは青で始まり、文字を入力するときは従来どおりcomboで文字入力モードへ切り替えます。
- **レイヤーの色。** 右手側の RGB LED がモードを示します。文字入力は緑、AI は青、数字キーパッドは黄、ゲームはシアン、ファンクションはマゼンタ、Bluetooth は赤、押しっぱなしの面を開いている間は白です。
- **deep sleep。** 左右とも無操作30分で眠ります（`CONFIG_ZMK_SLEEP=y`、`CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=1800000`）。起こすには右手側のキーを1回押す必要があり、その打鍵は送られません。
- **学習用表示器。** [`src/layer_uart.c`](src/layer_uart.c) が UART1（D1、送信のみ、9600 baud、8N1）で状態1 byte を送ります。起動時、レイヤーか押している修飾キーが変わったとき、キーを押したときに送り、bit 0〜2 が最高位のレイヤー、bit 3〜6 が Shift、Ctrl、Alt、GUI です。USB 給電の CH32V003 基板が透明 OLED に現在のキー配置を描きます。受信側のファームウェアは、このリポジトリの[`addons/oled/`](addons/oled/)に含まれます。使用する商品の名前、配線、書き込み方法は[学習用OLEDの導入手順](docs/oled-setup.md)にまとめています。右手側の `CONFIG_TINY18_LAYER_UART=y` で有効になります。

## キーマップ

キーマップの正本は [`config/tiny18.keymap`](config/tiny18.keymap) で、判断の理由はその中のコメントに書いてあります。[`build.yaml`](build.yaml) は左右に1種類ずつのファームウェアを作ります。ファームウェア関連のファイルを push すると GitHub Actions が [`keymap-drawer/tiny18.svg`](keymap-drawer/tiny18.svg) を描き直します。

![Tiny18 keymap](keymap-drawer/tiny18.svg)

| モード | レイヤー | 入り方 | 用途 |
| --- | --- | --- | --- |
| AI | 2 | `S + F` | 起動時のモード。左右の逆T字の矢印、Escape/Tab、BackSpace/Delete、Shift中の`/model`と`/status`、右手の句読点、左手のコピーと貼り付けのcombo、右手の元に戻す・やり直す・切り取り・検索のcombo |
| 文字入力 | 0 | `W + R` | 文字 |
| 数字キーパッド | 3 | `J + L` | テンキーのコード。日本語入力でも半角のまま通る |
| ゲーム | 5 | `R + S` | VRChat 用の WASD と、R I O P、チャット用のキー |
| ファンクション | 4 | `U + O` | F1 から F12 |
| Bluetooth | 1 | `O + J` | 接続プロファイルの切り替え |

モードの切り替えはモードごとに 2 キーの combo が 1 つです。ゲームモード内では AI モード行きとゲームモード行きが無効です。切替comboは打鍵後 150 ms おかないと効きません。ほかに親指を押さえている間だけ開く面が 2 つあります。BackSpace で数字と記号の面、Space か N で ZXCV の面です。面はレイヤー 6 と 7 で、いちばん大きい番号です。文字入力の親指を残しているモードから開けます。

キーは文字入力モードで出る文字の名前で呼びます。

- 文字入力の `A` はタップで A、350 ms 以上の長押しで Shift です。一度タップしてすぐにもう一度押さえ続けると、2回目は A のまま保持されて OS の自動反復になります。`Enter` は文字入力を含むすべてのモードと面で hold-tap です。軽く叩けば Enter、押さえれば Shift になります。AI モードと数字・記号の面では `A` の位置も Enter / Shift で、同じく左小指向けの判定は 350 ms です。ゲームモードの `A` の位置だけは素の Shift です。
- `BackSpace` を押さえると数字の面、`Space` か `N` を押さえると ZXCV の面、`M` を押さえると Ctrl です。左の親指 2 つは、数字キーパッドモードとゲームモード以外でこの割り当てです。
- `E + F` の同時押しで日本語と英語を切り替えます（Ctrl+Space）。文字入力モードだけで、打鍵後 150 ms おいてから効きます。AI モードの2つのslash commandは USB の `LANG2` キーを送り、Windows では IME オフ、macOS では英数として届くので、IME が日本語のままでも ASCII で届きます。
- キーを持たない文字は隣り合う 2 キーで出します。文字入力モードでは `Q T Y P G H`、ZXCV の面では `B` です。`A` はキーと combo の両方で出ます。
- Alt は `R + F`、GUI は `U + J` で、文字入力モードと AI モードで同じです。

## ダウンロード

導入または再配布には、`LICENSES/`を含むversioned統合ZIPを使います。過去の
[Releases](https://github.com/lunelukkio/zmk-config-tiny18/releases)には、対応する第三者
license資料がなく、UF2とchecksumだけのものがあります。これらは履歴・復旧用として
保持し、binaryだけを再配布しないでください。`v0.x.y`は実機確認中のpre-releaseで、
1.0より前の互換性は保証しません。`main`は最新のReleaseより進んでいることがあります。
最新の[ビルド実行](https://github.com/lunelukkio/zmk-config-tiny18/actions/workflows/build.yml)の
`firmware` artifactは期限付きのtest用で、完全なlicense bundleも含みません。

| ファイル | 書き込み先 |
| --- | --- |
| `tiny18-right.uf2` | 右手側。AI モードの矢印は普通の逆 T 字。Bluetooth 中央側、ZMK Studio 接続側、学習用表示器の送信側 |
| `tiny18-left.uf2` | 左手側。Bluetooth 周辺側 |
| `settings-reset.uf2` | 保存された Bluetooth・左右接続情報の消去 |
| `tiny18_layer.bin` | 任意のUIAPduino OLED受信機 |
| `VERSION.txt` | 共通バージョン、ソースの版、ビルド日時、Actions実行ID |
| `LICENSES/` | 依存ソフトウェアのライセンス本文・帰属表示 |
| `SHA256SUMS` | バンドル内の全ファイルのSHA-256チェックサム |

新しい統合版は`tiny18-vX.Y.Z.zip`として配布します。展開し、`LICENSES/`を
ファームウェアと一緒に保持してください。OLEDを使う場合は、3台分が揃った統合版を
選んでください。

左右のファイルは入れ替えられません。取り違えたら、もう一度ブートローダーへ入り、正しい UF2 を書き込んでください。キーマップを解釈するのは右手側だけです。左右とも同じビルドの UF2 を書き込んでください。

## 書き込み

1. キーボードのバッテリー電源を切り、USBデータケーブルで片側をPCへ接続します。
2. XIAO のリセットボタンを素早く2回押します。`XIAO-SENSE` ドライブが表示されます。
3. 右手側には `tiny18-right.uf2`、左手側には `tiny18-left.uf2` をコピーします。
4. USBを外して左右の電源を入れ、PCのBluetooth設定から `tiny18` をペアリングします。

OLEDも使う場合は、同じバージョンの`tiny18_layer.bin`をUIAPduinoへ書き込みます。手順は[OLEDの導入](docs/oled-setup.md)を参照してください。

初回導入時や接続不調時は、両側へ `settings-reset.uf2` を書き込んでから、改めて左右それぞれの UF2 を書き込んでください。PCに残っている古い `tiny18` のペアリングも削除してから再接続します。

右手側では ZMK Studio が有効です。Studio で編集したキーマップは設定領域に保存され、コンパイル済みのものより優先されます。書き込んだはずのキーマップが出てこないときは、先に `settings-reset.uf2` を書き込んでください。

## 自分でビルドする

ファームウェア関連ファイルを push すると GitHub Actions が3つの UF2 を自動ビルドします。ZMK と RGB LED モジュールはいずれも `v0.3.0` を指定しています。統合バンドルには解決後の依存commitも記録します。コンパイラやコンテナの更新で、バイナリが変わる場合があります。

1. このリポジトリを fork します。
2. fork 側で GitHub Actions を有効にします。
3. 必要なら `config/tiny18.keymap` を変更します。
4. push後、成功したActions実行の`firmware` artifactを個人の動作確認用に取得します。

Actions artifactは個人の動作確認用で期限があり、再配布に必要な完全なlicense bundleを
含みません。OLEDのビルドは別workflowなので、キーボードだけの利用・ビルドに
OLED用toolchainは不要です。`v0.3.1`のようなtagをpushすると、統合用workflowが
左右・リセット用UF2とOLEDをビルドし、ライセンス付きZIPを**未公開のRelease下書き**へ
添付します。レビューと実機確認後の公開は別操作です。
[ビルド・配布手順](docs/build-and-release.md)を参照してください。

### ビルドの内訳

[`build.yaml`](build.yaml) は次の3つを作ります。

- 右手側。RGB LED のレイヤー・電池表示、USB 経由の ZMK Studio、レイヤー送信用 UART 付き
- 左手側。RGB LED のレイヤー・電池表示付き
- 復旧用の settings-reset

## リポジトリの構成

| パス | 役割 |
| --- | --- |
| `config/tiny18.keymap` | キーマップの正本 |
| `config/tiny18_*.conf` | 左右それぞれの ZMK 設定。LED の色、deep sleep、右手側は ZMK Studio とレイヤー送信 UART |
| `boards/shields/tiny18/` | Tiny18 のシールド定義と direct-pin の配線。右手側の overlay が D1 に UART1 を足す |
| `src/layer_uart.c`、`src/start_in_ai.c`、`Kconfig`、`CMakeLists.txt`、`zephyr/module.yml` | 学習用表示器への送信とAIモードでの起動。このリポジトリ自体を Zephyr モジュールとしてビルドする |
| `build.yaml` | ビルドの組み合わせと成果物の名前 |
| `addons/oled/` | 任意の受信機、描画処理、固定版ch32fun submodule |
| `docs/tools/` | 共通のキーマップ・図・HTML・OLED生成ツールとテスト |
| `docs/oled-setup.md` | OLEDの商品名、配線、導入手順 |
| `tools/`、`tests/` | ローカルビルド、ライセンス収集、バンドル作成 |
| `firmware/` | ローカルの版別バンドル（生成物はGit管理外） |
| `keymap-drawer/` | 自動生成のキーマップ図 |
| `.github/workflows/build.yml` | 継続的ビルドと図の生成 |
| `.github/workflows/oled.yml` | 独立したOLEDビルドと生成ツール検査 |
| `.github/workflows/release.yml` | 統合Release下書きの作成。公開は手動 |

## 問い合わせ

不具合、導入手順についての質問、改善案は [GitHub Issues](https://github.com/lunelukkio/zmk-config-tiny18/issues) へ投稿してください。公開用のメールアドレスは設けず、通常の連絡窓口を Issues にまとめます。

## ハードウェア

配布対象はキーボード用と任意の学習用 OLED のソフトウェア、およびそのソース・説明書です。基板そのものと基板製造データは配布しません。本プロジェクトで使用した基板製造用 Gerber ファイルと、ケース・トッププレート用 STL ファイルが必要な場合は、元作者の有料記事 [Tiny18ビルドマニュアル：ver1／ver2のハードウェアと共通ファームウェア](https://note.com/3peta/n/n44d2c364cadc) から購入してください。購入したデータはこのリポジトリに含まれず、ミラー・改変版を含めて再配布できません。

一般的なハードウェア情報と、元作者が別途公開しているハードウェア資料は [Tiny18 ハードウェアリポジトリ](https://github.com/k3peta/tiny18) を参照してください。`boards/shields/` はファームウェアのビルドに必要なソフトウェア設定であり、基板製造データではありません。

## ライセンス

Tiny18 固有の設定・シールド定義は [MIT License](LICENSE) で公開します。上流の `Copyright (c) 2025-2026 k3peta` を保持し、lunelukkio が追加・変更した独自のソフトウェア部分にも MIT を適用します。その著作権表記は `Copyright (c) 2026 lunelukkio` です。

ZMK、Zephyr、外部ライブラリの著作権表示とライセンスは、それぞれ維持します。この fork の MIT によって依存ソフトウェアのライセンスを変更するものではありません。出典とファームウェア配布時の扱いは [ライセンスと配布範囲](docs/licensing.md) を参照してください。

購入した Gerber とケース・トッププレートの STL には再配布許可がありません。ミラー・改変版も含め、このリポジトリ、ソースのアーカイブ、ファームウェアのパッケージ、公開文書へ含めてはいけません。これらはソフトウェアの MIT ライセンスの対象外です。
