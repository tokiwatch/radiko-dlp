#!/usr/bin/env python3
"""config.tomlのschedule定義からcrontabのエントリを生成・反映する。"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from radiko_dlp.config import Config, ConfigError, load_config

DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.toml"
MARKER_BEGIN = "# BEGIN radiko-dlp (auto-generated, do not edit)"
MARKER_END = "# END radiko-dlp"
CONFIG_PREFIX = "# config: "


def build_block(config: Config, record_script: Path, config_path: Path) -> str:
    lines = [MARKER_BEGIN, f"{CONFIG_PREFIX}{config_path}"]
    for program in config.programs.values():
        if not program.schedule:
            continue
        lines.append(
            f"{program.schedule} {record_script} --config {config_path} {program.key}"
        )
    lines.append(MARKER_END)
    return "\n".join(lines) + "\n"


def current_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout


def registered_config(existing: str) -> str | None:
    """既存のcrontabの管理ブロックが、どの設定ファイルから登録されたかを返す。"""
    lines = existing.splitlines()
    if MARKER_BEGIN not in lines:
        return None
    for line in lines[lines.index(MARKER_BEGIN) + 1:]:
        if line == MARKER_END:
            break
        if line.startswith(CONFIG_PREFIX):
            return line[len(CONFIG_PREFIX):]
    return None


def merge_crontab(existing: str, block: str) -> str:
    lines = existing.splitlines()
    if MARKER_BEGIN in lines:
        start = lines.index(MARKER_BEGIN)
        end = lines.index(MARKER_END) + 1
        lines = lines[:start] + block.splitlines() + lines[end:]
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block.splitlines())
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--force", action="store_true", help="別の設定ファイルから登録済みの内容も上書きする")
    parser.add_argument("--apply", action="store_true", help="実際にcrontabへ反映する（省略時は表示のみ）")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"設定エラー: {exc}", file=sys.stderr)
        return 1

    record_script = Path(__file__).resolve().parent / "radiko-record"
    block = build_block(config, record_script, args.config.resolve())
    existing = current_crontab()
    registered = registered_config(existing)
    config_path = str(args.config.resolve())
    if registered and registered != config_path:
        message = (
            f"crontabには別の設定ファイル（{registered}）から登録された内容があります。"
            f"{config_path} の内容で置き換わります。"
        )
        if args.apply and not args.force:
            print(f"エラー: {message}\n置き換えてよい場合は --force を付けてください。", file=sys.stderr)
            return 1
        print(f"警告: {message}", file=sys.stderr)
    new_crontab = merge_crontab(existing, block)

    if not args.apply:
        print(new_crontab, end="")
        print("\n--apply を付けて実行すると上記をcrontabへ反映します", file=sys.stderr)
        return 0

    subprocess.run(["crontab", "-"], input=new_crontab, text=True, check=True)
    print("crontabを更新しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
