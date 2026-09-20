# radiko-cron マニュアル

[English](radiko-cron.md) | **日本語** · [README に戻る](../README.ja.md)

`radiko-cron` は、設定ファイルの各番組の `schedule` から crontab のエントリを作り、放送時刻に `radiko-record` が自動で実行されるようにするコマンドです。単独で実行できる実行ファイルなので、先頭に `python3` は不要です。

## 書式

```
./radiko-cron [--config CONFIG] [--apply] [--force]
```

| オプション | 内容 |
| --- | --- |
| `--config CONFIG` | 読み込む設定ファイル（省略時はスクリプトと同じ場所の `config.toml`） |
| `--apply` | 結果を実際に crontab へ反映する。付けない場合は、反映後の crontab を**表示するだけ**で、何も変更しない |
| `--force` | 別の設定ファイルから登録済みのブロックを、`--apply` で置き換えることを許可する（[保護の仕組み](#保護の仕組み)を参照） |

## 基本の流れ

```sh
# 1. config.toml の番組と schedule を書く（編集する）
# 2. プレビュー: 反映後の crontab 全体を表示する。何も変更しない
./radiko-cron

# 3. 反映する
./radiko-cron --apply

# 4. 確認する
crontab -l
```

変更されるのは、実行したユーザー自身の crontab だけです。root 権限は不要です。

## crontab に書かれる内容

`radiko-cron` が管理する内容は、2 つのコメント行で囲んだ 1 つのブロックにまとめられます。

```
# BEGIN radiko-dlp (auto-generated, do not edit)
# config: /home/user/radiko-dlp/config.toml
10 8 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml gendai_no_ongaku
0 16 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml suisogaku_no_hibiki
# END radiko-dlp
```

| 行 | 意味 |
| --- | --- |
| `# BEGIN radiko-dlp ...` / `# END radiko-dlp` | 管理ブロックの始まりと終わり |
| `# config: <パス>` | このブロックを生成した設定ファイル。保護の仕組みが使う |
| `<schedule> <radiko-record> --config <設定ファイル> <key>` | `schedule` を持つ番組ごとに 1 行。手で実行するときと同じ形の `./radiko-record --config <ファイル> <key>` |

ルール:

- **`schedule` を持つ番組ごとに 1 行。** `schedule` のない番組は登録されません（例: `sample.toml` のお試し用の番組）。
- **絶対パス。** `radiko-record` と設定ファイルは絶対パスで書かれるので、どのディレクトリからでも動きます。
- **書き換わるのはブロックの中だけ。** ブロックの外（ほかの cron ジョブ、`MAILTO=`、コメント）は、そのまま残ります。ブロックがまだなければ、末尾に追加されます。
- **何度実行しても同じ結果。** 設定が変わっていなければ、同じ crontab になります。
- **ブロックの中を手で編集しないでください。** 次の実行で上書きされます。
- 行に書かれるのは番組の `key` だけです。録音時間、保存先、ファイル名、局などは、`radiko-record` が実行のたびに設定ファイルから読み込みます。

## 再実行が必要なとき

| 変更した内容 | `--apply` のやり直し |
| --- | --- |
| 番組の `schedule` | **必要** |
| `schedule` を持つ番組の追加・削除 | **必要** |
| 番組の `key` | **必要**（crontab の行に key が入っているため） |
| リポジトリや設定ファイルの移動 | **必要**（行に絶対パスが入っているため） |
| `duration`、`output_dir`、`filename`、`station_url`、`name`、`[tools]` など | 不要。次の録音のときに設定から読み込まれる |

## 予約を削除するには

- **特定の番組だけ:** 設定ファイルからその番組の `schedule` の行（または番組ごと）を削除し、`./radiko-cron --apply` を実行します。crontab の行が消えます。
- **すべて:** すべての `schedule` を削除して `./radiko-cron --apply` を実行します。ブロックは残りますが、中に登録された行はなくなります。ブロック自体を消すには、`crontab -e` で `# BEGIN radiko-dlp` から `# END radiko-dlp` までの行を削除します。

## 保護の仕組み

- **既定はプレビュー。** `--apply` を付けない限り、何も反映されません。
- **別の設定ファイルは拒否。** crontab の管理ブロックは 1 つだけです。別の設定ファイルから生成されたブロックがあるとき、`--apply` は置き換えずに止まります。

  ```
  エラー: crontabには別の設定ファイル（/home/user/radiko-dlp/config.toml）から登録された内容があります。/home/user/radiko-dlp/sample.toml の内容で置き換わります。
  置き換えてよい場合は --force を付けてください。
  ```

  `sample.toml` のような別のファイルを試したときに、本番の予約が消えるのを防ぎます。本当に置き換えたいときだけ `--force` を付けてください。プレビュー（`--apply` なし）では、同じ内容が警告として表示されます。
- **壊れたブロックの検出。** `# END radiko-dlp` の行がない場合（手で消したときなど）は、エラーで止まり、何も変更しません。`crontab -e` で修正してください。
- **不正な schedule は cron が拒否。** `schedule` が cron の書式として正しくないと、`crontab` コマンドがファイル全体を受け付けません。その場合は、crontab が更新されなかったことを表示します。既存の crontab はそのままです。

## cron から実行されるときの注意

cron は、普段のシェルとは異なる最小限の環境でジョブを実行します。

- **`PATH` が最小限**（通常は `/usr/bin:/bin`）。`radiko-record` は `#!/usr/bin/env python3` で始まり、システムの Python で動きます。`yt-dlp` や `ffmpeg` が別の場所にある場合は、設定ファイルの `[tools]` に絶対パスで書いてください。
- **タイムゾーン。** cron はシステムのタイムゾーンで動き、番組表は日本時間です。マシンのタイムゾーンを `Asia/Tokyo` にしてください（`timedatectl` で確認できます）。
- **予定の時刻にマシンが起動している必要があります。** 実行できなかった予定が、あとから実行されることはありません。
- **実行後の確認先:**
  - 録音のログ: 各番組の `<output_dir>/logs/<key>.log`
  - cron がジョブを起動したか: `journalctl -u cron`（環境によっては syslog）

予約した行が動くかを確かめるには、crontab に書かれたコマンドを、cron に近い環境で手動実行します。`--test` を付けると、1 分だけ録音し、`<output_dir>/test/` に保存します。

```sh
env -i HOME="$HOME" PATH=/usr/bin:/bin SHELL=/bin/sh \
  /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml <key> --test
```

## 終了コード

| コード | 意味 |
| --- | --- |
| `0` | 成功（プレビューの表示、または crontab の更新） |
| `1` | エラー（設定エラー、別の設定ファイルの拒否、壊れたブロック、crontab による更新の拒否） |

## トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| `設定エラー: ...` | 設定ファイルがない、または内容が正しくありません。メッセージの原因を直します（[README](../README.ja.md#設定)を参照） |
| `別の設定ファイル ... から登録された内容があります` | 別の設定ファイルから登録されたブロックです。そのファイルを使うか、`--force` を付けて置き換えます |
| `管理ブロックに終端の行 ... がありません` | `# END radiko-dlp` の行が消えています。`crontab -e` で元に戻します |
| `crontabへの反映に失敗しました` | `schedule` の書式（`分 時 日 月 曜日`）を確認します |
| 予定の時刻に録音が始まらない | cron は動いているか（`systemctl is-active cron`）、タイムゾーンは Asia/Tokyo か、マシンは起動していたか、`crontab -l` にブロックがあるかを確認します。上の `env -i` の例でコマンドを手動実行します |
| 古い予定のまま動く | crontab は `--apply` を実行したときだけ更新されます。`schedule` を変更したら、もう一度実行してください |
