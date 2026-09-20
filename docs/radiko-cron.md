# radiko-cron manual

**English** | [日本語](radiko-cron.ja.md) · [Back to README](../README.md)

`radiko-cron` turns the `schedule` of every program in your config file into crontab entries, so that `radiko-record` runs automatically at broadcast time. It is a standalone executable (no `python3` prefix needed).

## Synopsis

```
./radiko-cron [--config CONFIG] [--dry-run] [--apply] [--force]
```

| Option | Description |
| --- | --- |
| `--config CONFIG` | Config file to read (default: `config.toml` next to the script) |
| `--dry-run` | Show what would be written to the crontab (the managed block and the difference from your current crontab) and change nothing. Wins over `--apply` if both are given |
| `--apply` | Actually install the result into your crontab. Without it, the tool behaves like `--dry-run` and changes nothing |
| `--force` | Allow `--apply` to replace a block that was registered from a *different* config file (see [Safety guards](#safety-guards)) |

## Typical workflow

```sh
# 1. Write or edit the programs (and their `schedule`) in config.toml
# 2. Preview what would be written (see "Previewing with --dry-run"). Nothing is changed
./radiko-cron --dry-run

# 3. Install it
./radiko-cron --apply

# 4. Check
crontab -l
```

Only your own user's crontab is touched. No root privileges are needed.

## Previewing with `--dry-run`

`./radiko-cron --dry-run` never changes your crontab. It prints the managed block that would be written, how many entries it contains, and a unified diff against your current crontab, so you can see exactly which lines are added, changed or removed:

```
crontabは変更しません（表示のみ）。反映すると、次の管理ブロックが書き込まれます（予約 2 件）:

# BEGIN radiko-dlp (auto-generated, do not edit)
# config: /home/user/radiko-dlp/config.toml
10 8 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml gendai_no_ongaku
5 16 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml suisogaku_no_hibiki
# END radiko-dlp

現在のcrontabとの差分:
--- 現在のcrontab
+++ 反映後のcrontab
@@ -3,5 +3,5 @@
 # BEGIN radiko-dlp (auto-generated, do not edit)
 # config: /home/user/radiko-dlp/config.toml
 10 8 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml gendai_no_ongaku
-0 16 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml suisogaku_no_hibiki
+5 16 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml suisogaku_no_hibiki
 # END radiko-dlp

実際に反映するには、--dry-run を付けずに --apply を付けて実行してください。
```

- Lines starting with `-` disappear, lines starting with `+` are added. Everything else is unchanged context.
- If nothing would change, the diff section says `差分: なし`.
- If the crontab holds a block from a different config file, a warning is printed as well (see [Safety guards](#safety-guards)).
- `--dry-run` also wins when combined with `--apply`, so it is safe to add it to a command line you are about to run.

## What is written to the crontab

`radiko-cron` keeps everything it manages inside one block, marked by two comment lines:

```
# BEGIN radiko-dlp (auto-generated, do not edit)
# config: /home/user/radiko-dlp/config.toml
10 8 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml gendai_no_ongaku
0 16 * * 0 /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml suisogaku_no_hibiki
# END radiko-dlp
```

| Line | Meaning |
| --- | --- |
| `# BEGIN radiko-dlp ...` / `# END radiko-dlp` | Start and end of the managed block |
| `# config: <path>` | The config file the block was generated from. Used by the safety guard |
| `<schedule> <radiko-record> --config <config> <key>` | One line per program that has a `schedule`. The command is the same form you type by hand: `./radiko-record --config <file> <key>` |

Rules:

- **One line per scheduled program.** Programs without a `schedule` are skipped (for example the trial program in `sample.toml`).
- **Absolute paths.** The lines contain the absolute paths of `radiko-record` and of the config file, so they work regardless of the current directory.
- **Only the block is rewritten.** Everything outside the block (your other cron jobs, `MAILTO=`, comments) is left exactly as it is. If there is no block yet, it is appended at the end.
- **Idempotent.** Running it again with an unchanged config produces the same crontab.
- **Do not edit the block by hand.** Manual edits inside it are overwritten by the next run.
- The lines contain only the program `key`. Everything else (duration, output directory, filename, station) is read from the config file every time `radiko-record` runs.

## When to run it again

| You changed | Run `--apply` again? |
| --- | --- |
| `schedule` of a program | **Yes** |
| Added or removed a program that has a `schedule` | **Yes** |
| A program's `key` | **Yes** (the crontab line contains the key) |
| Moved the repository or the config file | **Yes** (the lines contain absolute paths) |
| `duration`, `output_dir`, `filename`, `station_url`, `name`, `[tools]` ... | No. Taken from the config at the next recording |

## Removing a schedule

- **One program:** delete its `schedule` line (or the whole program) from the config file, then run `./radiko-cron --apply`. Its crontab line disappears.
- **All programs:** remove every `schedule` and run `./radiko-cron --apply`. The block stays, but contains no entries. To remove the block itself, run `crontab -e` and delete the lines from `# BEGIN radiko-dlp` to `# END radiko-dlp`.

## Safety guards

- **Preview by default.** Nothing is installed unless you pass `--apply`, and `--dry-run` always prevents installing.
- **A different config file is refused.** The crontab holds a single managed block. If it was generated from another config file, `--apply` stops instead of replacing it:

  ```
  エラー: crontabには別の設定ファイル（/home/user/radiko-dlp/config.toml）から登録された内容があります。/home/user/radiko-dlp/sample.toml の内容で置き換わります。
  置き換えてよい場合は --force を付けてください。
  ```

  This protects your real schedule when you try another file such as `sample.toml`. Add `--force` only when you really want to replace it. A preview (`--dry-run`, or no `--apply`) prints the same message as a warning.
- **A damaged block is reported.** If the `# END radiko-dlp` line is missing (for example deleted by hand), the tool stops with an error and changes nothing. Fix it with `crontab -e`.
- **Invalid schedules are rejected by cron.** If a `schedule` is not valid cron syntax, the `crontab` command refuses the whole file and the tool reports that the crontab was not updated. Your existing crontab stays as it was.

## Running under cron

Cron runs jobs in a minimal environment, which is different from your shell:

- **`PATH` is minimal** (usually `/usr/bin:/bin`). `radiko-record` starts with `#!/usr/bin/env python3`, which works with the system Python. If `yt-dlp` or `ffmpeg` are installed somewhere else, write their absolute paths in `[tools]` of the config file.
- **Time zone.** Cron uses the system time zone, and program guides are in Japan time. Make sure the machine is set to `Asia/Tokyo` (check with `timedatectl`).
- **The machine must be on** at the scheduled time. A missed schedule is not run later.
- **Where to look afterwards:**
  - Recording log: `<output_dir>/logs/<key>.log` for each program
  - Whether cron started the job: `journalctl -u cron` (or the syslog on your system)

To check that a scheduled line will work, run the exact command from the crontab under a cron-like environment. Add `--test` to record only one minute into `<output_dir>/test/`:

```sh
env -i HOME="$HOME" PATH=/usr/bin:/bin SHELL=/bin/sh \
  /home/user/radiko-dlp/radiko-record --config /home/user/radiko-dlp/config.toml <key> --test
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (a preview, or the crontab was updated) |
| `1` | Error: configuration error, a different config file was refused, a damaged block, or the crontab rejected the update |

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `設定エラー: ...` | The config file is missing or invalid. Fix the message's cause (see the [README](../README.md#configuration)) |
| `別の設定ファイル ... から登録された内容があります` | The block was registered from another config file. Use that file, or add `--force` to replace it |
| `管理ブロックに終端の行 ... がありません` | The `# END radiko-dlp` line was removed. Restore it with `crontab -e` |
| `crontabへの反映に失敗しました` | Check the `schedule` syntax (`minute hour day month weekday`) |
| The recording did not start at the scheduled time | Is cron running (`systemctl is-active cron`)? Is the time zone Asia/Tokyo? Was the machine on? Does `crontab -l` show the block? Try the command under `env -i` as shown above |
| The line still runs an old program | The crontab is only updated by `--apply`. Run it again after changing the `schedule` |
