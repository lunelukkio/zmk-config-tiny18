# ライセンスと配布範囲

## 配布するもの

配布対象はキーボード用と任意の学習用 OLED のソフトウェア、その source と
説明書です。基板そのものと基板製造データは配布せず、元作者の入手先を案内します。
`boards/shields/` のような firmware の build に必要な設定は、ソフトウェアとして
配布対象に含めます。基板現物を配布しなくても、UF2 に含まれる ZMK や Zephyr の
ライセンス条件は適用されます。

## この fork のソフトウェア

[LICENSE](../LICENSE) は MIT License です。元作者の
`Copyright (c) 2025-2026 k3peta` を保持し、lunelukkio が追加・変更した
独自のソフトウェア部分には `Copyright (c) 2026 lunelukkio` を記載します。
上流のコードを自分の著作物として扱うものではありません。

MIT は、著作権表示と許諾文を維持する条件で、使用・改変・再配布・販売を
認めます。第三者のソフトウェアとハードウェアのデータには、各自の条件が
適用されます。原文は [MIT License](https://opensource.org/license/mit) を参照してください。

## ZMK と Zephyr の関係

キーボードの UF2 は複数のソフトウェアを組み合わせて作ります。自分の追加部分を
MIT にしても、組み込んだ第三者のコードは元のライセンスのままです。

| 対象 | ライセンスと範囲 | 出典 |
| --- | --- | --- |
| Tiny18 の元の設定・シールド定義 | MIT、k3peta の表示を保持 | [上流の LICENSE](https://github.com/k3peta/zmk-config-tiny18/blob/main/LICENSE) |
| この fork の独自の追加・変更部分 | MIT、lunelukkio の表示 | [この fork の LICENSE](../LICENSE) |
| ZMK v0.3.0 本体 | MIT | [使用版の LICENSE](https://github.com/zmkfirmware/zmk/blob/v0.3.0/LICENSE) |
| ZMK の基盤である Zephyr | 主に Apache-2.0。一部の取り込みコードは別のライセンス | [使用版の LICENSE](https://github.com/zmkfirmware/zephyr/blob/v3.5.0%2Bzmk-fixes/LICENSE)、[ライセンスの説明](https://docs.zephyrproject.org/latest/LICENSING.html) |
| 学習用 OLED の ch32fun | repository の LICENSE は MIT。取り込むファイル固有の表示も保持 | [固定 commit の LICENSE](https://github.com/cnlohr/ch32fun/blob/50b6e591f466231bf3e3ea2c184b3c686e93d755/LICENSE) |

ZMK の版は [config/west.yml](../config/west.yml) にあり、Zephyr の版は
[ZMK v0.3.0 の manifest](https://github.com/zmkfirmware/zmk/blob/v0.3.0/app/west.yml)
で指定されています。表は主要なソフトウェアの説明であり、完成したバイナリの
全依存を確認済みとする一覧ではありません。OLEDのsourceと固定版ch32funは
[`addons/oled/`](../addons/oled/)に含まれます。submodule内の元の表示も保持します。

Apache-2.0 も改変・再配布を認めています。配布時にはライセンス本文を渡し、
配布する source の関係する著作権・帰属表示を保持します。Apache-2.0 のファイルを
変更した場合は変更したことを明記し、上流の配布物に NOTICE があれば、関係する
帰属表示も引き継ぎます。自分の独自部分を MIT で提供する方針と両立します。
詳細は [Apache License 2.0 の第4条](https://www.apache.org/licenses/LICENSE-2.0#redistribution)
が正本です。

配布用パッケージには、この fork の LICENSE と、実際に組み込む依存ソフトウェアの
ライセンス本文・必要な帰属表示を同梱します。README にリンクだけを置くことを
同梱の代わりにはしません。統合版の[配布用workflow](../.github/workflows/release.yml)は、
実際のbuildに使ったwest workspaceからライセンス本文とC/Rust sourceの帰属コメントを
収集し、ch32funとSDK runtimeのライセンスもZIPの`LICENSES/`へ同梱します。
Git projectの依存commitは`LICENSES/inventory.json`と`resolved-west.yml`に記録します。
SDK runtimeは、使用した版、公式配布元、同梱したlicense file一覧を
`inventory.json`に記録します。

この収集処理は、未使用のmodule・fileも含む保守的な資料作成です。
バイナリへlinkされた全コードのライセンスを自動判定したり、再配布条件への適合を
保証したりするものではありません。v0.3.1のlocal review buildでは、OLEDの最終mapに
ch32funの`misc/libgcc.a`から`muldi3.o`の`__mulsi3`だけが22 bytes残り、`div.o`は
discardされています。対応する`misc/LIBGCC_LICENSE`はch32funの資料として同梱します。
compilerやsourceが変わればlink結果も変わり得るため、SDK runtimeとファイル固有の条件を
毎回buildのmapと照合し、レビューを通してからRelease下書きを公開します。
旧ReleaseのUF2へ、この統合版の収集結果をそのまま流用しないでください。

## 旧形式のbinaryとActions artifact

ライセンス付きのversioned ZIPを、新しい統合版の再配布単位とします。旧形式の公開
Releaseには、個別のUF2とchecksumだけで、対応する第三者license資料が付属しないものが
あります。通常の`build.yml`と`oled.yml`が作る期限付きActions artifactも、binaryだけで
完全なlicense bundleを含みません。これらは履歴確認・個人の動作確認用であり、binaryを
単独で再配布するための完全なpackageとしては扱いません。再配布する場合は、対象sourceと
依存に対応する`LICENSES/`を含む統合ZIPを作り直してください。この文書の更新だけでは、
既存Releaseのasset追加・取り下げやActions artifactの構成変更は行いません。

## 再配布禁止のハードウェアデータ

購入した Gerber とケース・トッププレートの STL には再配布許可がありません。
ミラー・改変版を含め、公開 repository、source のアーカイブ、firmware の
パッケージ、公開文書へ含めてはいけません。これらに本ソフトウェアの MIT を
適用することもできません。

本プロジェクトで使用した Gerber とケース・トッププレートの STL が必要な場合は、
元作者の有料記事 [Tiny18ビルドマニュアル：ver1／ver2のハードウェアと共通ファームウェア](https://note.com/3peta/n/n44d2c364cadc)
から購入してください。記事の有料部分には、基板発注用 Gerber とケース・
トッププレート用 STL が含まれます。購入したデータを、この repository の
一部として再配布することはできません。

元作者が GitHub で公開している基板製造データは別の配布物で、CERN-OHL-P-2.0
です。このライセンスを購入データの再配布許可として扱ってはいけません。
一般的なハードウェア情報と、元作者が別途公開している資料は
[元作者の hardware repository](https://github.com/k3peta/tiny18) を参照してください。
