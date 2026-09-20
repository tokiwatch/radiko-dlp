# radiko-dlp

[English](README.md) | **日本語**

[radiko.jp](https://radiko.jp/) のライブ放送（NHK・民放）を、yt-dlp と ffmpeg でスケジュール録音するツールです。NHK は らじる★らじる のプレーヤー経由でも録音できます。

番組は `config.toml` に一度書いておくだけです。録音時に radiko の番組表から放送中の回を調べ、その回のタイトル・出演者・説明を、ファイルのタグとファイル名に記録します。

## 特長

- 複数の番組を 1 つの TOML ファイル（`config.toml`）で管理
- `yt-dlp` + `ffmpeg` でライブ配信を `.m4a`（AAC）に録音
- radiko の番組表から放送回の情報を取得し、タグ（`title`、`artist`、`album`、`date`、`comment`）とファイル名（`{title}`）に記録
- 各番組の `schedule` から crontab のエントリを生成・更新
- 録音できない局（NHK ラジオ第2、エリア外の局、存在しない局ID）は、録音の前に分かりやすいメッセージで中止
- 番組表が取得できなくても、録音そのものは止まらない
- Python の外部パッケージは不要（標準ライブラリのみ。venv も不要）

## 必要なもの

- Python 3.11 以上（標準ライブラリの `tomllib` を使用）
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)（既定のパス: `/usr/bin/yt-dlp`）
- ffmpeg（既定のパス: `/usr/bin/ffmpeg`）
- cron（`crontab` コマンド）。スケジュール録音をする場合のみ

yt-dlp や ffmpeg が別の場所にある場合は、`config.toml` の `[tools]` に書く（[ツールのパス](#ツールのパス)を参照）か、`radiko-record` に `--yt-dlp` / `--ffmpeg` で指定します。

## クイックスタート

```sh
git clone https://github.com/tokiwatch/radiko-dlp.git
cd radiko-dlp

# 1. 試してみる: まず確認だけ行い（録音しない）、NHK-FM を今すぐ 1 分間録音する
#    （sample.toml を使用。保存先: ~/Music/radiko/quickstart/）
./radiko-record quickstart --config sample.toml --dry-run
./radiko-record quickstart --config sample.toml

# 2. ひな形から自分用の設定を作り、編集する（「設定」を参照）
cp config.example.toml config.toml

# 3. 自分の番組を確認し、録音する
./radiko-record sample_program --dry-run
./radiko-record sample_program

# 4. crontab の内容をプレビューし、反映する
./manage_cron.py
./manage_cron.py --apply
```

- 手順 1 は、実行するとすぐ録音を始め、1 分後に終了します（`sample.toml` は `duration = "00:01:00"` で `schedule` がないため、cron には登録されません）。`--dry-run` は録音しません。
- `JOAK-FM` は東京の NHK-FM です。東京エリア以外ではエリア外のメッセージが出て中止するので、`sample.toml` の局IDを変更してください（[対応する局と制約](#対応する局と制約)を参照）。
- 手順 3 も、実行するとすぐ録音を始め、設定した `duration`（ひな形では 51 分）の間続きます。先に `--dry-run` を使うか、試すときは `duration` を短くしてください。
- 自動で録音が始まるのは、手順 4 のあとの `schedule` の時刻です。

`radiko-record` と `manage_cron.py` は実行ファイルなので、先頭に `python3` は不要です。

## 設定

番組は `config.toml` に書きます。ひな形をコピーして作成してください（`cp config.example.toml config.toml`）。`config.toml` は個人用のファイルで、git では管理されません。番組ごとに `[[programs]]`（角括弧が 2 つ）のブロックを 1 つ追加します。

```toml
[[programs]]
key = "sample_program"
name = "サンプル番組"
station_url = "https://radiko.jp/#!/live/JOAK-FM"
duration = "00:51:00"
schedule = "10 8 * * 0"
output_dir = "~/Music/radiko/sample_program"
filename = "{date}_{title}.m4a"
```

| 項目 | 必須 | 内容 |
| --- | --- | --- |
| `key` | 必須 | コマンドや crontab から参照する一意の識別子 |
| `name` | 必須 | 番組名。`album` タグになり、番組表が使えないときはタイトルの代わりになる |
| `station_url` | 必須 | `https://radiko.jp/#!/live/<局ID>`。NHK のプレーヤーを使う場合は `https://www.nhk.or.jp/radio/player/?ch=r1` または `ch=fm` |
| `duration` | 必須 | 録音時間（`HH:MM:SS`）。番組の長さ + 1 分ほどが目安 |
| `output_dir` | 必須 | 保存先ディレクトリ（なければ作成）。`~` は展開される |
| `filename` | 任意 | ファイル名テンプレート。省略時は `{date}_{key}.m4a`。使えるのは `{date}`、`{key}`、`{title}` |
| `schedule` | 任意 | cron 形式（`分 時 日 月 曜日`）。`manage_cron.py` が使う。省略した番組は登録されない |
| `station_id` | 任意 | 番組表の取得に使う局ID。`station_url` が NHK のプレーヤーの URL のときに必要（例: `"JOAK-FM"`） |

TOML の注意点: 文字列は必ず `"` で囲みます。`#` から行末まではコメントです。`key` は重複させないでください。

ひな形の `config.example.toml` には、コメントアウトしたサンプル（NHK ラジオ第1、らじる★らじる 経由の NHK FM、TBS、文化放送、ニッポン放送、吹奏楽のひびき、サンデー・ソングブック）も入っています。自分の `config.toml` にコピーし、先頭の `# ` を外して使ってください。

### ツールのパス

`yt-dlp` と `ffmpeg` の場所は、省略可能な `[tools]` テーブルで指定できます。どちらの項目も省略できます。

```toml
[tools]
yt_dlp = "/usr/local/bin/yt-dlp"
ffmpeg = "/usr/bin/ffmpeg"
```

- 既定値は `/usr/bin/yt-dlp` と `/usr/bin/ffmpeg` です。
- コマンド名だけ（`"yt-dlp"`）を書くと `PATH` から探します。`~` は展開されます。cron の `PATH` は最小限なので、定期実行では絶対パスで書くのが確実です。
- 優先順位は、コマンドラインの `--yt-dlp` / `--ffmpeg`、`[tools]`、既定値の順です。
- 設定した `ffmpeg` は、録音とタグの書き込みの両方に使われます。
- 見つからない、または実行できない場合、`radiko-record` は設定エラー（終了コード `1`）で止まります。`--dry-run` でも同じ確認をします。

### cron の書き方（早見表）

| 書き方 | 意味 |
| --- | --- |
| `10 8 * * 0` | 毎週日曜 08:10（曜日は 0 が日曜、6 が土曜） |
| `0 22 * * 1-5` | 平日 22:00 |
| `30 7 * * 1,3,5` | 月・水・金の 07:30 |

時刻は番組の開始時刻に合わせます。

## 番組情報の記録

開始時刻に、その局のその日の番組表を取得し、録音する時間帯（開始時刻から開始時刻 + `duration` まで）と重なりが最大の番組を選びます。このため `duration` は番組の実際の長さに近い値にしてください。極端に長いと、次の番組が選ばれることがあります。

| 記録先 | 内容 |
| --- | --- |
| ファイル名 `{title}` | 放送回のタイトル。全角文字は半角に正規化（NFKC）、`\ / : * ? " < > \|` と制御文字は `_` に置換、150 バイトまでに切り詰め |
| タグ `title` | 放送回のタイトル |
| タグ `artist` | 番組表の出演者（`(司会)` などの役割が付くことがある） |
| タグ `album` | `config.toml` の `name` |
| タグ `date` | 放送日（`YYYY-MM-DD`） |
| タグ `comment` | 放送回の説明と番組ページの URL |

番組表が取得できないときは、警告をログに出して録音を続けます。その場合、`{title}` と `title` タグには `name` が使われます。タグの書き込みに失敗した場合も、録音ファイルは残り、エラーがログに記録されます。

## cron での定期実行

`manage_cron.py` は、`schedule` を持つ**番組ごとに 1 行**を、crontab の管理ブロックに書き込みます。常駐するプログラムを入れるわけではなく、行も短いものです。

```
# BEGIN radiko-dlp (auto-generated, do not edit)
10 8 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml sample_program
# END radiko-dlp
```

- 書き換わるのは `# BEGIN radiko-dlp` と `# END radiko-dlp` の間だけです。ほかの crontab のエントリには触れません。何度実行しても結果は同じです。
- `radiko-record` は実行のたびに `config.toml` を読み直します。`duration`、`output_dir`、`filename`、`station_url` などの変更は、再登録しなくても次の録音から反映されます。
- `schedule` の変更、番組の追加・削除、`key` の変更、リポジトリの移動（行に絶対パスが入っているため）をしたときは、`./manage_cron.py --apply` をやり直してください。
- ブロックの中を手で編集しても、次の実行で上書きされます。
- 予定の時刻にマシンが起動している必要があります。

## 対応する局と制約

- **ライブ放送のみ。** 過去の放送（radiko のタイムフリー）には対応していません。放送時刻に合わせて録音を実行する必要があります。
- **エリア制限。** radiko の無料版は、接続元エリアの局しか聴取できません（エリアフリー・プレミアムには未対応）。他のエリアの局を指定すると、メッセージを出して中止します。
- **NHK ラジオ第2（JOAB）は非対応。** radiko では配信されておらず、NHK 自身の第2放送のストリームのホスト名も、現在は名前解決できません。
- **らじる★らじる 経由の NHK。** `ch=r1` と `ch=fm` は録音できます。番組表は引き続き radiko から取得するため、`station_id`（第1は `"JOAK"`、FM は `"JOAK-FM"`）を指定してください。

東京エリアで使える局ID（radiko の局一覧で確認済み）:

| ID | 局 | ID | 局 |
| --- | --- | --- | --- |
| `JOAK` | NHK AM（東京） | `FMT` | TOKYO FM |
| `JOAK-FM` | NHK FM（東京） | `FMJ` | J-WAVE |
| `TBS` | TBSラジオ | `INT` | interfm |
| `QRR` | 文化放送 | `JORF` | ラジオ日本 |
| `LFR` | ニッポン放送 | `NACK5` | NACK5 |
| `RN1` / `RN2` | ラジオNIKKEI 第1 / 第2 | `BAYFM78` | BAYFM78 |
| `YFM` | ＦＭヨコハマ | `IBS` | LuckyFM 茨城放送 |

他のエリアの局は、radiko でその局を開いて URL（`https://radiko.jp/#!/live/<ID>`）から局IDを確認するか、`curl -s --compressed https://radiko.jp/v3/station/list/JP27.xml` のようにエリアの局一覧を取得します（エリアIDは `JP1`〜`JP47` で、都道府県コード順です）。

## コマンドリファレンス

### `radiko-record`

```
./radiko-record [--config CONFIG] [--yt-dlp PATH] [--ffmpeg PATH] [--dry-run] key
```

| オプション | 内容 |
| --- | --- |
| `key` | `config.toml` の番組の `key` |
| `--config` | 設定ファイルのパス（省略時はスクリプトと同じ場所の `config.toml`） |
| `--yt-dlp`、`--ffmpeg` | 実行ファイルのパス。`config.toml` の `[tools]` より優先される（既定: `/usr/bin/yt-dlp`、`/usr/bin/ffmpeg`） |
| `--dry-run` | 局を確認し、番組表を取得して、実行コマンドとタグを表示する。録音せず、ファイルも作らない |

ログは `<output_dir>/logs/<key>.log` に追記されます。警告とエラーは標準エラー出力にも表示されます。

終了コード:

| コード | 意味 |
| --- | --- |
| `0` | 録音できた（タグの書き込み失敗はログに残るだけ） |
| `1` | 設定エラー、または `yt-dlp` の失敗（`yt-dlp` の終了コードをそのまま返す） |
| `2` | 録音できない局（NHK ラジオ第2、エリア外、存在しない局ID、日本国外） |

### `manage_cron.py`

```
./manage_cron.py [--config CONFIG] [--apply]
```

`--apply` を付けないと、反映後の crontab を表示するだけです。`--apply` を付けると実際に反映します。

## トラブルシューティング

| 症状 | 確認すること |
| --- | --- |
| `エラー: ... は録音できません` / 終了コード `2` | メッセージを読んでください。非対応の局、エリア外の局、`station_url` の局IDの誤りのいずれかです |
| `警告: 番組表を利用できないため...` | 番組表を取得できませんでした。録音は行われ、タイトルには `name` が使われます |
| タイトルが別の回になる | `schedule` が開始時刻と合っているか、`duration` が番組の長さに近いかを確認します |
| `yt-dlp` が失敗する | `<output_dir>/logs/<key>.log` を確認します。yt-dlp を更新してください（radiko の仕様変更で古い版が動かなくなることがあります） |
| `yt-dlp が見つからないか実行できません`（ffmpeg も同様） | `config.toml` の `[tools]` のパスを直すか、`--yt-dlp` / `--ffmpeg` で指定します |
| cron で録音されなかった | `crontab -l` にブロックがあるか、マシンが起動していたか、ログがあるかを確認し、crontab と同じコマンドを手で実行します |
| `filename` の `未知のプレースホルダー` | 使えるのは `{date}`、`{key}`、`{title}` だけです |

## 開発

```
radiko-record        録音コマンド（実行ファイル）
manage_cron.py       crontab の生成
sample.toml          クイックスタート用サンプル（NHK-FM を 1 分録音）
config.example.toml  config.toml のひな形
config.toml          自分用の番組定義（git 管理外）
radiko_dlp/
  config.py          設定の読み込みと検証
  guide.py           番組表の取得とファイル名の整形
  station.py         局の確認（エリア、NHK ラジオ第2）
tests/               単体テスト
```

テストの実行:

```sh
python3 -m unittest discover -s tests
```

## 注意

録音した音源は、お住まいの国の著作権法が認める私的利用の範囲で利用してください。このプロジェクトは、株式会社radiko および NHK とは関係ありません。
