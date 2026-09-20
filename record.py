#!/usr/bin/env python3
"""config.tomlで定義した番組をyt-dlp+ffmpegで録音し、番組表の情報をタグとファイル名に反映する。"""
from __future__ import annotations

import argparse
import logging
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from radiru_dlp.config import ConfigError, Program, load_config
from radiru_dlp.guide import (
    JST,
    GuideError,
    ProgramInfo,
    fetch_program,
    sanitize_filename_part,
    station_id_from_url,
)
from radiru_dlp.station import StationError, check_station

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.toml"
EXIT_STATION_UNAVAILABLE = 2


def build_command(ffmpeg_path: str, yt_dlp_path: str, program: Program, output_path: Path) -> list[str]:
    return [
        yt_dlp_path,
        "--downloader", ffmpeg_path,
        "--downloader-args",
        f"ffmpeg_i:-t {program.duration} -seekable 0 -http_seekable 0",
        program.station_url,
        # yt-dlpは-oを出力テンプレートとして解釈するため、リテラルの%をエスケープする
        "-o", str(output_path).replace("%", "%%"),
    ]


def lookup_guide(program: Program, start: datetime) -> tuple[ProgramInfo | None, str | None]:
    try:
        station_id = program.station_id or station_id_from_url(program.station_url)
        return fetch_program(station_id, start, program.duration_seconds), None
    except GuideError as exc:
        return None, str(exc)


def build_tags(program: Program, info: ProgramInfo | None, start: datetime) -> dict[str, str]:
    if info is None:
        tags = {"title": program.name, "album": program.name, "date": f"{start:%Y-%m-%d}"}
    else:
        comment = "\n".join(part for part in (info.description, info.url) if part)
        tags = {
            "title": info.title,
            "artist": info.performers,
            "album": program.name,
            "date": f"{info.start:%Y-%m-%d}",
            "comment": comment,
        }
    return {key: value for key, value in tags.items() if value}


def build_output_path(program: Program, info: ProgramInfo | None, start: datetime) -> Path:
    date = (info.start if info else start).strftime("%Y-%m-%d")
    title = sanitize_filename_part(info.title if info else program.name)
    try:
        filename = program.filename.format(date=date, key=program.key, title=title)
    except KeyError as exc:
        raise ConfigError(f"filenameに未知のプレースホルダーがあります: {exc}") from None
    return Path(program.output_dir).expanduser() / filename


def embed_metadata(ffmpeg_path: str, audio_path: Path, tags: dict[str, str]) -> None:
    tmp_path = audio_path.with_name(f"{audio_path.stem}.tagged{audio_path.suffix}")
    command = [ffmpeg_path, "-y", "-loglevel", "error", "-i", str(audio_path), "-map", "0", "-c", "copy"]
    for key, value in tags.items():
        command += ["-metadata", f"{key}={value}"]
    command.append(str(tmp_path))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(result.stderr.strip())
    tmp_path.replace(audio_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", help="config.toml内のprogramsで指定したkey")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="設定ファイルのパス")
    parser.add_argument("--yt-dlp", default="/usr/bin/yt-dlp")
    parser.add_argument("--ffmpeg", default="/usr/bin/ffmpeg")
    parser.add_argument("--dry-run", action="store_true", help="番組表を取得してコマンドとタグを表示するだけで録音しない")
    args = parser.parse_args(argv)

    start = datetime.now(JST)
    try:
        program = load_config(args.config).get(args.key)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(program.output_dir).expanduser()
    if not args.dry_run:
        log_dir = output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=log_dir / f"{program.key}.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

    def warn(message: str) -> None:
        print(f"警告: {message}", file=sys.stderr)
        if not args.dry_run:
            logging.warning(message)

    try:
        station_warning = check_station(program)
    except StationError as exc:
        print(f"エラー: 「{program.name}」({program.key}) は録音できません。{exc}", file=sys.stderr)
        if not args.dry_run:
            logging.error("録音できない局のため中止しました: %s", exc)
        return EXIT_STATION_UNAVAILABLE
    if station_warning:
        warn(station_warning)

    info, guide_error = lookup_guide(program, start)
    if guide_error:
        warn(f"番組表を利用できないため設定の番組名で録音します: {guide_error}")
    try:
        output_path = build_output_path(program, info, start)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        return 1

    tags = build_tags(program, info, start)
    command = build_command(args.ffmpeg, args.yt_dlp, program, output_path)

    if args.dry_run:
        print(shlex.join(command))
        for key, value in tags.items():
            print(f"  {key}: {value}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logging.info("録音開始: %s -> %s", program.name, output_path)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error("録音失敗 (exit=%s): %s", result.returncode, result.stderr.strip())
        return result.returncode

    logging.info("録音完了: %s", output_path)
    try:
        embed_metadata(args.ffmpeg, output_path, tags)
        logging.info("メタデータを記録しました: %s", tags.get("title"))
    except RuntimeError as exc:
        logging.error("メタデータの記録に失敗しました（録音ファイルは保持）: %s", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
