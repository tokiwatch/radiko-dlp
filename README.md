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
filename = "{date}_{title}.m4a"
```

| 項目 | 内容 |
| --- | --- |
| `key` | `record.py`やcrontabから参照する一意の識別子 |
| `name` | 番組名（ログ表示用） |
| `station_url` | radiko.jpのライブページURL |
| `duration` | 録音時間（`HH:MM:SS`） |
| `schedule` | cron形式のスケジュール（`manage_cron.py`で使用、省略可） |
| `output_dir` | 保存先ディレクトリ |
| `filename` | 出力ファイル名テンプレート（`{date}`, `{key}`, `{title}`が使用可能） |
| `station_id` | 番組表の局ID（省略時は`station_url`の`/live/`以降から取得） |

## 番組情報の記録

録音開始時刻に放送中の番組（録音時間内で重なりが最大の番組）を radiko の番組表から取得し、次のように反映します。

- ファイル名: `{title}` に放送回のタイトルが入ります（全角英数字は半角に正規化し、使えない文字は `_` に置換）
- m4a のタグ: `title`（放送回タイトル）、`artist`（出演者）、`album`（configの`name`）、`date`（放送日）、`comment`（番組説明と番組ページURL）

番組表を取得できなかった場合も録音は続行し、`{title}`と`title`タグにはconfigの`name`を使います（警告はログに出力）。

## 使い方

### 手動で録音する

```sh
python3 record.py gendai_no_ongaku
```

番組表を取得し、実行コマンドと書き込まれるタグを確認するだけ（録音しない）場合は `--dry-run` を付けます。

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

## テスト

```sh
python3 -m unittest discover -s tests
```
