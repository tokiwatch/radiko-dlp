#!/usr/bin/env python3
"""config.tomlで定義した番組をyt-dlp+ffmpegで録音する。"""
from __future__ import annotations

import argparse
import logging
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path

from radiru_dlp.config import ConfigError, Program, load_config

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.toml"


def build_command(ffmpeg_path: str, yt_dlp_path: str, program: Program, output_path: Path) -> list[str]:
    return [
        yt_dlp_path,
        "--downloader", ffmpeg_path,
        "--downloader-args",
        f"ffmpeg_i:-t {program.duration} -seekable 0 -http_seekable 0",
        program.station_url,
        "-o", str(output_path),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", help="config.toml内のprogramsで指定したkey")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="設定ファイルのパス")
    parser.add_argument("--yt-dlp", default="/usr/bin/yt-dlp")
    parser.add_argument("--ffmpeg", default="/usr/bin/ffmpeg")
    parser.add_argument("--dry-run", action="store_true", help="コマンドを表示するだけで実行しない")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        program = config.get(args.key)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(program.output_dir).expanduser()
    filename = program.filename.format(date=date.today().isoformat(), key=program.key)
    output_path = output_dir / filename
    command = build_command(args.ffmpeg, args.yt_dlp, program, output_path)

    if args.dry_run:
        print(shlex.join(command))
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = output_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=log_dir / f"{program.key}.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    logging.info("録音開始: %s -> %s", program.name, output_path)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error("録音失敗 (exit=%s): %s", result.returncode, result.stderr.strip())
    else:
        logging.info("録音完了: %s", output_path)
    if result.stdout:
        logging.debug(result.stdout)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
