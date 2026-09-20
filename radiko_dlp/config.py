from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Program:
    key: str
    name: str
    station_url: str
    duration: str
    output_dir: str
    filename: str = "{date}_{key}.m4a"
    schedule: str | None = None
    station_id: str | None = None

    @property
    def duration_seconds(self) -> int:
        hours, minutes, seconds = (int(part) for part in self.duration.split(":"))
        return hours * 3600 + minutes * 60 + seconds


DEFAULT_YT_DLP = "/usr/bin/yt-dlp"
DEFAULT_FFMPEG = "/usr/bin/ffmpeg"
TOOL_KEYS = ("yt_dlp", "ffmpeg")


@dataclass(frozen=True)
class Config:
    programs: dict[str, Program]
    yt_dlp: str = DEFAULT_YT_DLP
    ffmpeg: str = DEFAULT_FFMPEG

    def get(self, key: str) -> Program:
        try:
            return self.programs[key]
        except KeyError:
            raise ConfigError(
                f"番組 '{key}' が見つかりません（config内のkey一覧: {sorted(self.programs)}）"
            ) from None


REQUIRED_FIELDS = ("key", "name", "station_url", "duration", "output_dir")


def resolve_tool(option: str, configured: str) -> str:
    """設定されたパス（またはPATH上のコマンド名）を実行可能ファイルの絶対パスに解決する。"""
    found = shutil.which(os.path.expanduser(configured))
    if not found:
        raise ConfigError(
            f"{option} が見つからないか実行できません: {configured}"
            f"（config.toml の [tools] または --{option} でパスを指定してください）"
        )
    return found


def _load_tools(data: dict) -> dict[str, str]:
    tools = data.get("tools", {})
    if not isinstance(tools, dict):
        raise ConfigError("[tools] はテーブルで指定してください")
    unknown = sorted(set(tools) - set(TOOL_KEYS))
    if unknown:
        raise ConfigError(f"[tools] に未知の項目があります: {unknown}（使えるのは {list(TOOL_KEYS)}）")
    for key, value in tools.items():
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"[tools] の {key} は空でない文字列で指定してください: {value!r}")
    return {key: os.path.expanduser(value) for key, value in tools.items()}


def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(
            f"設定ファイルが見つかりません: {path}（config.example.toml をコピーして作成できます）"
        )

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"設定ファイルの書式が正しくありません ({path}): {exc}") from None

    programs: dict[str, Program] = {}
    for entry in data.get("programs", []):
        missing = [field for field in REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ConfigError(f"programエントリに必須項目が不足しています: {missing} ({entry})")
        key = entry["key"]
        if key in programs:
            raise ConfigError(f"番組keyが重複しています: {key}")
        programs[key] = Program(
            key=key,
            name=entry["name"],
            station_url=entry["station_url"],
            duration=entry["duration"],
            output_dir=entry["output_dir"],
            filename=entry.get("filename", "{date}_{key}.m4a"),
            schedule=entry.get("schedule"),
            station_id=entry.get("station_id"),
        )
        try:
            programs[key].duration_seconds
        except ValueError:
            raise ConfigError(
                f"durationは HH:MM:SS 形式で指定してください: {key} ({entry['duration']})"
            ) from None

    if not programs:
        raise ConfigError("programsが1件も定義されていません")

    return Config(programs=programs, **_load_tools(data))
