from __future__ import annotations

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


@dataclass(frozen=True)
class Config:
    programs: dict[str, Program]

    def get(self, key: str) -> Program:
        try:
            return self.programs[key]
        except KeyError:
            raise ConfigError(
                f"番組 '{key}' が見つかりません（config内のkey一覧: {sorted(self.programs)}）"
            ) from None


REQUIRED_FIELDS = ("key", "name", "station_url", "duration", "output_dir")


def load_config(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(f"設定ファイルが見つかりません: {path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

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

    return Config(programs=programs)
