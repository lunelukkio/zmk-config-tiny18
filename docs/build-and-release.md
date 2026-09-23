# ビルドと統合バンドルの準備

キーボードの利用が主で、OLEDは任意です。通常の利用者は公開済みReleaseのZIPを
展開して書き込みます。以下はソースを変更する人と配布を準備する人の手順です。
コマンドはWindows PowerShell 5.1、clone先は`~/zmk-config-tiny18`の例です。

## 1. ソースを取得する

キーボードだけなら通常のcloneで十分です。

```powershell
Set-Location ~; git clone https://github.com/lunelukkio/zmk-config-tiny18.git
```

OLEDもビルドする場合だけ、公開ライブラリch32funを取得します。
GitHubの自動生成「Source code ZIP」にはsubmoduleの内容は含まれないため、
OLED開発にはGitで取得してください。

```powershell
Set-Location ~\zmk-config-tiny18; git submodule update --init --recursive
```

## 2. 図・HTML・OLED表示を再生成する

Pythonの実行には[uv](https://docs.astral.sh/uv/getting-started/installation/)を使います。
図には日本語フォントが必要です。WindowsはMeiryo、LinuxはNoto Sans CJKを自動検出します。
別のフォントを使う場合は`TINY18_FONT`と`TINY18_FONT_BOLD`でフォントファイルを指定します。
フォント本体はこのリポジトリに含めません。

```powershell
Set-Location ~\zmk-config-tiny18; uv run --no-project --with pillow python docs/tools/make_chart.py
Set-Location ~\zmk-config-tiny18; uv run --no-project --with pillow python docs/tools/build_html.py
Set-Location ~\zmk-config-tiny18; uv run --no-project --with pillow python docs/tools/make_oled_layers.py
Set-Location ~\zmk-config-tiny18; uv run --no-project --with pillow python -m unittest discover -s docs/tools
Set-Location ~\zmk-config-tiny18; uv run --no-project --with pyyaml python -m unittest discover -s tests
```

各行が成功したことを確認してから次へ進みます。出力はそれぞれ
`docs/tiny18-keymap.png`、`docs/keymap.html`、`addons/oled/layers.h`です。
HTMLはローカルで開けます。別のサイトやプロジェクトには書き込みません。
図とHTML本文、OLEDの表示を変更したキーと照合し、生成物も同じ変更へ含めます。

## 3. キーボードをビルドする

### GitHub Actions

forkでActionsを有効にすると、`build.yml`が`build.yaml`の3イメージを作ります。
`firmware` artifactに左右とリセット用UF2が入ります。OLEDのworkflowが失敗しても、
このキーボードjobはOLEDに依存しません。Actionsの実行はソースのpushを伴うため、
公開前レビューが必要な作業では、先に下記のローカルビルドを使います。
通常の`firmware` artifactとOLED artifactは個人の動作確認用で、binaryだけを含み、
完全なlicense bundleは含みません。再配布には、`LICENSES/`を含むversioned統合ZIPを
使ってください。

### ローカル（Docker Desktop、Linux containers）

[ZMK v0.3.0の公式workflow](https://github.com/zmkfirmware/zmk/blob/v0.3.0/.github/workflows/build-user-config.yml)
と同じSDKイメージ、board、shield、snippet、CMake設定を使います。
最初は依存ソースを多数取得するため、空き容量と時間が必要です。
ローカルとActionsでコンテナや依存の解決時点が異なる場合、バイナリまで同一になる
保証はありません。

```powershell
Set-Location ~\zmk-config-tiny18
$repoPath = (Get-Location).Path
New-Item -ItemType Directory -Force build\zmk | Out-Null
docker run --rm --env CMAKE_BUILD_PARALLEL_LEVEL=4 `
  --mount "type=bind,source=$repoPath,target=/repo,readonly" `
  --mount "type=bind,source=$repoPath\build\zmk,target=/workspace" `
  zmkfirmware/zmk-build-arm:stable bash /repo/tools/build-keyboard.sh /workspace
```

結果は`build/zmk/firmware/`です。`build/zmk/resolved-west.yml`には実際の依存commitが
残ります。既存ソースを消す処理はありません。ZMKの版やboardを変える場合は、
別の空のbuild workspaceを使い、古いCMake設定を流用しないでください。

## 4. OLEDをビルドする（任意）

[OLED開発手順](../addons/oled/README.md)のRISC-V compilerとGNU Makeを用意します。

```powershell
Set-Location ~\zmk-config-tiny18\addons\oled; make OS=Windows_NT PREFIX=riscv-none-elf tiny18_layer.bin
```

`make`の既定動作はビルドのみです。実機への書き込みは[導入手順](oled-setup.md)で
別に行います。配布者が統合バンドルを作る場合は、OLEDを使わなくてもBINを揃えます。

## 5. ライセンスと版別フォルダを作る（配布者向け）

まず、使用したSDKのruntime licenseを取り出します。以下は最初の収集時の例です。
すでに同名の収集結果がある場合は、別の空の出力先を使ってください。

```powershell
Set-Location ~\zmk-config-tiny18
$repoPath = (Get-Location).Path
docker run --rm --mount "type=bind,source=$repoPath\build,target=/out" `
  zmkfirmware/zmk-build-arm:stable bash -c 'set -euo pipefail; shopt -s nullglob; sdk_roots=(/opt/zephyr-sdk-*); test "${#sdk_roots[@]}" -eq 1; sdk_root="${sdk_roots[0]}"; cp -RL "$sdk_root/arm-zephyr-eabi/share/licenses" /out/sdk-licenses; printf "%s\n" "${sdk_root##*/zephyr-sdk-}" > /out/sdk-version.txt'
```

`-L`でSDK内のリンクを通常ファイルへ展開します。これを省くと、Windowsから
ライセンス本文を読めず、収集やZIP作成が失敗する場合があります。同時に
`sdk-version.txt`へ使用したSDKの版を保存します。

依存元のライセンス本文・帰属コメント・commit一覧を収集します。
収集先がすでに存在すると処理は停止します。

```powershell
Set-Location ~\zmk-config-tiny18
$sdkVersion = (Get-Content -Raw build\sdk-version.txt).Trim()
uv run --no-project --with pyyaml python tools/export_licenses.py --workspace build/zmk `
  --sdk-licenses build/sdk-licenses --sdk-version $sdkVersion --output build/LICENSES
```

次に新しいバージョンのフォルダとZIPを作ります。下記の`v0.3.1`は例です。
既存の版を上書きせず、1.0未満は動作変更ならminor、意図した動作を変えない修正なら
patchを増やします。Actionsのrun IDをフォルダ名にはしません。

```powershell
Set-Location ~\zmk-config-tiny18
$sourceCommit = git rev-parse HEAD
uv run --no-project python tools/package_firmware.py --version v0.3.1 `
  --keyboard build/zmk/firmware --licenses build/LICENSES `
  --source-commit $sourceCommit --source-state local-review-worktree
```

`firmware/v0.3.1/`と`firmware/tiny18-v0.3.1.zip`が生成されます。必須ファイルが欠ける、
UF2形式が不正、OLEDが16 KBを超える、または同じ版が既にある場合は作成を拒否します。
`VERSION.txt`は未commitのローカルレビュー用ソースを使ったことと、Actions未実行を
明記します。公開版はレビュー済みcommit/tagから作り直し、Actions run IDを記録します。

## 6. 公開前レビューとRelease

1. キーマップ、図、OLED画面、配線説明、公開範囲をレビューします。
2. `LICENSES/`とbuildのmapを照合し、第三者の再配布条件を確認します。
   自動収集は全依存の法的な適合判定ではありません。[詳細](licensing.md)を参照してください。
3. Gerber・STL・秘密情報・個人PCのパスが、Git差分と配布ZIPへ混ざっていないか確認します。
4. 左右とOLEDの実機を確認します。旧版は削除せず、戻せるよう保持します。
5. **ここまでがローカルの公開準備です。push・tagの送信は別の承認後に行います。**
6. 承認後にversion tagを送ると、`release.yml`が同じソースから両方をビルドし、
   ライセンス付きZIPをGitHub Releaseの**下書き**へ添付します。自動公開しません。
7. 下書きの内容・checksum・版を確認し、公開を明示的に承認した後に公開します。

GitHubのリポジトリ自体がpublicの場合、ソースやtagのpush時点でそれらは公開されます。
Releaseが下書きであることは、ソースの非公開を意味しません。
キーボードだけの利用者はZIP内のOLED BINを使わなくて構いません。
