from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from radiko_dlp.config import Program

TEST_DURATION = "00:01:00"
TEST_SUBDIR = "test"


def apply_test_mode(program: Program) -> Program:
    """録音時間を短縮し、保存先をtest/以下にして、本番の録音と混ざらないようにする。"""
    duration = program.duration if program.duration_seconds < 60 else TEST_DURATION
    output_dir = Path(program.output_dir).expanduser() / TEST_SUBDIR
    return replace(program, duration=duration, output_dir=str(output_dir))


def unique_path(path: Path) -> Path:
    """同名のファイルがあれば _2, _3 ... を付けた名前にして、既存の録音を上書きも省略もしない。"""
    if not path.exists():
        return path
    number = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{number}{path.suffix}")
        if not candidate.exists():
            return candidate
        number += 1
