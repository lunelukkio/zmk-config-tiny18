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
全依存を確認済みとする一覧ではありません。OLED の source 統合は別の作業です。

Apache-2.0 も改変・再配布を認めています。配布時にはライセンス本文を渡し、
配布する source の関係する著作権・帰属表示を保持します。Apache-2.0 のファイルを
変更した場合は変更したことを明記し、上流の配布物に NOTICE があれば、関係する
帰属表示も引き継ぎます。自分の独自部分を MIT で提供する方針と両立します。
詳細は [Apache License 2.0 の第4条](https://www.apache.org/licenses/LICENSE-2.0#redistribution)
が正本です。

配布用パッケージには、この fork の LICENSE と、実際に組み込む依存ソフトウェアの
ライセンス本文・必要な帰属表示を同梱します。README にリンクだけを置くことを
同梱の代わりにはしません。現在の配布物については、全依存の確認とライセンスの
同梱が別途必要です。

## 再配布禁止のハードウェアデータ

購入した Gerber とケース・トッププレートの STL には再配布許可がありません。
ミラー・改変版を含め、公開 repository、source のアーカイブ、firmware の
パッケージ、公開文書へ含めてはいけません。これらに本ソフトウェアの MIT を
適用することもできません。

元作者が GitHub で公開している基板製造データは別の配布物で、CERN-OHL-P-2.0
です。このライセンスを購入データの再配布許可として扱ってはいけません。
基板の入手先は [元作者の hardware repository](https://github.com/k3peta/tiny18)
へ案内します。
