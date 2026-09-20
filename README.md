# radiko-dlp

**English** | [日本語](README.ja.md)

Scheduled recording of live radio from [radiko.jp](https://radiko.jp/) (NHK and commercial stations) using yt-dlp and ffmpeg. NHK stations can also be recorded through NHK's own らじる★らじる player.

Each program is described once in `config.toml`. At recording time the tool looks up the airing episode in radiko's program guide, then records it and writes the episode's title, performers and description into the file's tags and filename.

## Features

- Define any number of programs in a single TOML file (`config.toml`)
- Records the live stream with `yt-dlp` + `ffmpeg` into `.m4a` (AAC)
- Fetches the episode information from radiko's program guide and writes it to the tags (`title`, `artist`, `album`, `date`, `comment`) and to the filename (`{title}`)
- Generates and updates crontab entries from the `schedule` of each program
- Fails early with a clear message for stations that cannot be recorded (NHK Radio 2, stations outside your area, unknown station IDs)
- Recording never stops just because the program guide is unavailable
- No third-party Python packages (standard library only, no venv needed)

## Requirements

- Python 3.11 or later (uses the standard-library `tomllib`)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (default path: `/usr/bin/yt-dlp`)
- ffmpeg (default path: `/usr/bin/ffmpeg`)
- cron (`crontab` command), only if you want scheduled recording

If yt-dlp or ffmpeg are installed elsewhere, set their paths in `[tools]` of `config.toml` (see [Tool paths](#tool-paths)) or pass `--yt-dlp` / `--ffmpeg` to `radiko-record`.

## Quick start

```sh
git clone https://github.com/tokiwatch/radiko-dlp.git
cd radiko-dlp

# 1. Try it: check first (records nothing), then record NHK-FM for 1 minute right now
#    (uses sample.toml; the file is saved to ~/Music/radiko/quickstart/)
./radiko-record --config sample.toml quickstart --dry-run
./radiko-record --config sample.toml quickstart

# 2. Create your own config from the template, then edit it (see "Configuration")
cp config.example.toml config.toml

# 3. Check your own program, then try a 1-minute test recording
./radiko-record sample_program --dry-run
./radiko-record sample_program --test

# 4. Preview the crontab lines, then register them
./radiko-cron
./radiko-cron --apply
```

- The command form is `./radiko-record [--config FILE] <key>`, the same form that `radiko-cron` writes into crontab. `<key>` is the `key` of one program defined in the config file (`quickstart` in `sample.toml`, `sample_program` in `config.toml`). Without `--config`, `config.toml` is used.
- Only the program with that `key` is recorded. If a config file defines several programs, the others are not touched; run the command once per program.
- Step 1 starts recording immediately and stops after about one minute (`sample.toml` sets `duration = "00:01:00"` and has no `schedule`, so nothing is registered in cron). `--dry-run` never records.
- `JOAK-FM` is NHK-FM Tokyo. Outside the Tokyo area the command stops with an area message; change the station ID in `sample.toml` (see [Stations and limitations](#stations-and-limitations)).
- Step 3: `--test` records only 1 minute and saves into the `test/` subdirectory of the program's `output_dir`, so a trial never mixes with the real recordings. **Without `--test`, the command records for the full `duration` right away into the real `output_dir`.**
- After step 4, recording starts automatically only at the `schedule` times.

`radiko-record` and `radiko-cron` are executable scripts, so `python3` is not needed in front of them.

## Configuration

Programs are defined in `config.toml`. Create it by copying the template (`cp config.example.toml config.toml`); it is your personal file and is not tracked by git. Add one `[[programs]]` block (double brackets) per program.

```toml
[[programs]]
key = "sample_program"
name = "Sample Program"
station_url = "https://radiko.jp/#!/live/JOAK-FM"
duration = "00:01:00"
schedule = "10 8 * * 0"
output_dir = "~/Music/radiko/sample_program"
filename = "{date}_{title}.m4a"
```

| Field | Required | Description |
| --- | --- | --- |
| `key` | yes | Unique identifier used on the command line and in crontab |
| `name` | yes | Program name. Used as the `album` tag, and as the fallback title when the guide is unavailable |
| `station_url` | yes | `https://radiko.jp/#!/live/<station ID>`. For NHK's own player use `https://www.nhk.or.jp/radio/player/?ch=r1` or `ch=fm` |
| `duration` | yes | Recording length as `HH:MM:SS`. Use the program length plus about one minute |
| `output_dir` | yes | Destination directory (created if missing). `~` is expanded |
| `filename` | no | Filename template. Default: `{date}_{key}.m4a`. Placeholders: `{date}`, `{key}`, `{title}` |
| `schedule` | no | Cron expression (`minute hour day month weekday`). Used by `radiko-cron`; programs without it are not scheduled |
| `station_id` | no | Station ID used for the program guide. Needed when `station_url` is an NHK player URL (e.g. `"JOAK-FM"`) |

Notes on TOML: strings must be quoted, `#` starts a comment, and `key` must be unique.

The template `config.example.toml` also contains commented-out samples (NHK R1, NHK FM via らじる★らじる, TBS, 文化放送, ニッポン放送, 吹奏楽のひびき, サンデー・ソングブック). Copy one into your `config.toml` and remove the leading `# `.

### Tool paths

The locations of `yt-dlp` and `ffmpeg` can be set in an optional `[tools]` table. Both entries are optional.

```toml
[tools]
yt_dlp = "/usr/local/bin/yt-dlp"
ffmpeg = "/usr/bin/ffmpeg"
```

- Defaults: `/usr/bin/yt-dlp` and `/usr/bin/ffmpeg`.
- A bare command name (`"yt-dlp"`) is looked up on `PATH`; `~` is expanded. Cron runs with a minimal `PATH`, so absolute paths are the safer choice for scheduled recording.
- Priority: `--yt-dlp` / `--ffmpeg` on the command line, then `[tools]`, then the defaults.
- The configured `ffmpeg` is used both for recording and for writing the tags.
- If a tool cannot be found or is not executable, `radiko-record` stops with a configuration error (exit code `1`). `--dry-run` performs the same check.

### Cron schedule cheat sheet

| Expression | Meaning |
| --- | --- |
| `10 8 * * 0` | Every Sunday at 08:10 (weekday: 0 = Sunday, 6 = Saturday) |
| `0 22 * * 1-5` | Weekdays at 22:00 |
| `30 7 * * 1,3,5` | Mon / Wed / Fri at 07:30 |

Set the time to when the program starts.

## Program information

At start time the tool fetches the day's guide for the station and picks the program that overlaps most with the recording window (start time to start time + `duration`). That is why `duration` should be close to the program's real length: a much longer value may select the following program.

| Written to | Content |
| --- | --- |
| Filename `{title}` | Episode title. Full-width characters are normalized to half-width (NFKC); `\ / : * ? " < > \|` and control characters become `_`; truncated to 150 bytes |
| Tag `title` | Episode title |
| Tag `artist` | Performers as listed in the guide (may include roles such as `(司会)`) |
| Tag `album` | `name` from `config.toml` |
| Tag `date` | Broadcast date (`YYYY-MM-DD`) |
| Tag `comment` | Episode description and program page URL |

If a file with the same name already exists (for example the same episode recorded twice on one day), the new recording is saved as `<name>_2.m4a`, `_3`, and so on. An existing recording is never overwritten or skipped, so a manual run cannot cause a scheduled recording to be lost.

If the guide cannot be fetched, a warning is logged and recording continues: `{title}` and the `title` tag fall back to `name`. If tagging itself fails, the recording is kept and an error is logged.

## Scheduling with cron

`radiko-cron` writes **one line per program that has a `schedule`**, inside a managed block of your crontab. It does not install a resident process, and the lines are short:

```
# BEGIN radiko-dlp (auto-generated, do not edit)
# config: /home/user/radiko-dlp/config.toml
10 8 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml sample_program
# END radiko-dlp
```

- Only the block between `# BEGIN radiko-dlp` and `# END radiko-dlp` is rewritten; every other crontab entry is left alone. Running it repeatedly gives the same result.
- `radiko-record` reads `config.toml` every time it runs, so changes to `duration`, `output_dir`, `filename`, `station_url` and so on take effect at the next recording without re-registering.
- Re-run `./radiko-cron --apply` after changing a `schedule`, adding or removing a program, changing a `key`, or moving the repository (the lines contain absolute paths).
- Edits you make by hand inside the block are overwritten on the next run.
- The machine must be powered on at the scheduled time.

## Stations and limitations

- **Live only.** Past broadcasts (radiko time-free) are not supported, so recording must run at broadcast time.
- **Area restriction.** The free version of radiko only lets you listen to stations in the area of your connection (area-free / premium is not supported). Choosing a station from another area fails with a message.
- **NHK Radio 2 (JOAB) is not supported.** It is not offered on radiko, and NHK's own stream host for Radio 2 currently does not resolve.
- **NHK through らじる★らじる.** `ch=r1` and `ch=fm` work; the program guide still comes from radiko, so set `station_id` (`"JOAK"` for Radio 1, `"JOAK-FM"` for FM).

Station IDs available in the Tokyo area (verified against radiko's station list):

| ID | Station | ID | Station |
| --- | --- | --- | --- |
| `JOAK` | NHK AM (Tokyo) | `FMT` | TOKYO FM |
| `JOAK-FM` | NHK FM (Tokyo) | `FMJ` | J-WAVE |
| `TBS` | TBS Radio | `INT` | interfm |
| `QRR` | 文化放送 | `JORF` | ラジオ日本 |
| `LFR` | ニッポン放送 | `NACK5` | NACK5 |
| `RN1` / `RN2` | ラジオNIKKEI 第1 / 第2 | `BAYFM78` | BAYFM78 |
| `YFM` | ＦＭヨコハマ | `IBS` | LuckyFM 茨城放送 |

For other areas, open the station on radiko and copy the ID from the URL (`https://radiko.jp/#!/live/<ID>`), or list an area's stations with `curl -s --compressed https://radiko.jp/v3/station/list/JP27.xml` (area IDs are `JP1`–`JP47`, in prefecture order).

## Command reference

### `radiko-record`

```
./radiko-record [--config CONFIG] [--yt-dlp PATH] [--ffmpeg PATH] [--test] [--dry-run] key
```

| Option | Description |
| --- | --- |
| `key` | The `key` of a program in `config.toml` |
| `--config` | Path to the config file (default: `config.toml` next to the script) |
| `--yt-dlp`, `--ffmpeg` | Paths to the executables. They override `[tools]` in `config.toml` (default: `/usr/bin/yt-dlp`, `/usr/bin/ffmpeg`) |
| `--test` | Trial recording: records at most 1 minute and saves into `<output_dir>/test/` (logs too), leaving the real `output_dir` untouched. Prints the saved path when done |
| `--dry-run` | Check the station, fetch the guide, and print the command and the tags. Records nothing and creates no files |

Logs are appended to `<output_dir>/logs/<key>.log`. Warnings and errors are also printed to stderr.

Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Recorded (a tagging failure is only logged) |
| `1` | Configuration error, or `yt-dlp` failed (its exit code is passed through) |
| `2` | The station cannot be recorded (NHK Radio 2, outside your area, unknown ID, outside Japan) |

### `radiko-cron`

```
./radiko-cron [--config CONFIG] [--apply] [--force]
```

Without `--apply` it only prints the resulting crontab. With `--apply` it installs it.

The managed block records which config file it was generated from (the `# config:` line). Running `--apply` with a different config file (for example `sample.toml`) is refused unless you add `--force`, so trying another file cannot wipe your real schedule.

## Troubleshooting

Messages printed by the tool (and written to the log) are in Japanese.

| Symptom | What to check |
| --- | --- |
| `エラー: ... は録音できません` ("cannot be recorded") / exit code `2` | Read the message: unsupported station, station outside your area, or a wrong station ID in `station_url` |
| `警告: 番組表を利用できないため...` ("program guide unavailable") | The guide could not be fetched. The recording still runs, with `name` used as the title |
| Wrong episode in the title | Check `schedule` matches the start time, and that `duration` is close to the program length |
| `yt-dlp` fails | See `<output_dir>/logs/<key>.log`. Update yt-dlp: radiko changes can break older versions |
| `yt-dlp が見つからないか実行できません` ("yt-dlp not found or not executable"; same for ffmpeg) | Fix the path in `[tools]` of `config.toml`, or pass `--yt-dlp` / `--ffmpeg` |
| Nothing was recorded by cron | `crontab -l` shows the block; the machine was on; the log exists. Try the exact crontab command by hand |
| `未知のプレースホルダー` ("unknown placeholder") in `filename` | Only `{date}`, `{key}` and `{title}` are available |

## Development

```
radiko-record        recording command (executable script)
radiko-cron        crontab generator
sample.toml          quick start sample (records NHK-FM for 1 minute)
config.example.toml  template for config.toml
config.toml          your program definitions (not tracked by git)
radiko_dlp/
  config.py          config loading and validation
  guide.py           program guide lookup and filename sanitizing
  station.py         station availability checks (area, NHK Radio 2)
tests/               unit tests
```

Run the tests with:

```sh
python3 -m unittest discover -s tests
```

## Notice

Use recordings within the limits of private use under the copyright law of your country. This project is not affiliated with radiko Co., Ltd. or NHK.
