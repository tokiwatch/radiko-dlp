from __future__ import annotations

import html
import re
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
GUIDE_URL = "https://radiko.jp/v3/program/station/date/{date}/{station}.xml"
STATION_RE = re.compile(r"/live/([A-Za-z0-9_-]+)")
# radikoの番組表は5:00始まりの放送日単位
BROADCAST_DAY_START_HOUR = 5
FILENAME_MAX_BYTES = 150


class GuideError(Exception):
    pass


@dataclass(frozen=True)
class ProgramInfo:
    title: str
    start: datetime
    end: datetime
    performers: str
    description: str
    url: str


def station_id_from_url(url: str) -> str:
    match = STATION_RE.search(url)
    if not match:
        raise GuideError(f"station_urlから局IDを取得できません: {url}")
    return match.group(1)


def _clean_text(raw: str | None) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw or "", flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=JST)


def parse_guide(xml_text: str) -> list[ProgramInfo]:
    root = ET.fromstring(xml_text)
    return [
        ProgramInfo(
            title=(prog.findtext("title") or "").strip(),
            start=_parse_time(prog.get("ft")),
            end=_parse_time(prog.get("to")),
            performers=(prog.findtext("pfm") or "").strip(),
            description=_clean_text(prog.findtext("info")) or _clean_text(prog.findtext("desc")),
            url=(prog.findtext("url") or "").strip(),
        )
        for prog in root.iter("prog")
    ]


def pick_program(programs: list[ProgramInfo], start: datetime, duration_seconds: int) -> ProgramInfo | None:
    end = start + timedelta(seconds=duration_seconds)

    def overlap(program: ProgramInfo) -> timedelta:
        return min(program.end, end) - max(program.start, start)

    best = max(programs, key=overlap, default=None)
    if best is None or overlap(best) <= timedelta(0):
        return None
    return best


def fetch_program(station_id: str, start: datetime, duration_seconds: int, timeout: float = 15) -> ProgramInfo:
    broadcast_date = (start - timedelta(hours=BROADCAST_DAY_START_HOUR)).strftime("%Y%m%d")
    url = GUIDE_URL.format(date=broadcast_date, station=station_id)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            programs = parse_guide(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
        raise GuideError(f"番組表の取得に失敗しました ({url}): {exc}") from exc

    program = pick_program(programs, start, duration_seconds)
    if program is None:
        raise GuideError(f"{start:%Y-%m-%d %H:%M} に該当する番組が番組表にありません ({url})")
    return program


def sanitize_filename_part(text: str, max_bytes: int = FILENAME_MAX_BYTES) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    while len(text.encode("utf-8")) > max_bytes:
        text = text[:-1]
    return text.strip(" .")
