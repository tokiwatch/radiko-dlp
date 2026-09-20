# radiru-dlp

NHK らじる★らじる（radiko.jp経由）の番組を、yt-dlp + ffmpeg でスケジュール録音するためのツールです。

## 必要なもの

- Python 3.11以降（`tomllib`を標準ライブラリとして使用）
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- ffmpeg

## 設定

`config.toml` に録音したい番組を `[[programs]]` として登録します。

```toml
[[programs]]
key = "gendai_no_ongaku"
name = "現代の音楽"
station_url = "https://radiko.jp/#!/live/JOAK-FM"
duration = "00:51:00"
schedule = "10 8 * * 0"
output_dir = "/home/tokiwa/Music/NHK/gendai_no_ongaku"
filename = "{date}_gendai_no_ongaku.m4a"
```

| 項目 | 内容 |
| --- | --- |
| `key` | `record.py`やcrontabから参照する一意の識別子 |
| `name` | 番組名（ログ表示用） |
| `station_url` | radiko.jpのライブページURL |
| `duration` | 録音時間（`HH:MM:SS`） |
| `schedule` | cron形式のスケジュール（`manage_cron.py`で使用、省略可） |
| `output_dir` | 保存先ディレクトリ |
| `filename` | 出力ファイル名テンプレート（`{date}`, `{key}`が使用可能） |

## 使い方

### 手動で録音する

```sh
python3 record.py gendai_no_ongaku
```

コマンドを確認するだけ（実行しない）場合は `--dry-run` を付けます。

```sh
python3 record.py gendai_no_ongaku --dry-run
```

ログは `output_dir/logs/<key>.log` に出力されます。

### crontabに反映する

`config.toml`の`schedule`をもとにcrontabへ反映します。デフォルトでは反映後の内容を表示するだけです。

```sh
python3 manage_cron.py          # 反映内容をプレビュー
python3 manage_cron.py --apply  # 実際にcrontabへ反映
```

既存のcrontabのうち `# BEGIN radiru-dlp` 〜 `# END radiru-dlp` の間だけを書き換え、それ以外のエントリはそのまま保持します。
