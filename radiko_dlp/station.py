from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urlparse

from radiko_dlp.config import Program
from radiko_dlp.guide import STATION_RE, fetch_text

AREA_URL = "https://radiko.jp/area"
AREA_STATIONS_URL = "https://radiko.jp/v3/station/list/{area}.xml"
FULL_STATIONS_URL = "https://radiko.jp/v3/station/region/full.xml"
AREA_RE = re.compile(r'class="([A-Za-z0-9_]+)"')

NHK_RADIO2_MESSAGE = (
    "NHKラジオ第2は現在録音に対応していません"
    "（radikoでは配信されておらず、らじる★らじるの配信も利用できないため）。"
)

# radikoのエリアID(JP1〜JP47)は都道府県コード順
PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県",
    "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県",
    "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)


class StationError(Exception):
    """指定された局は録音に対応していない、または現在の環境では録音できない。"""


def area_label(area_id: str) -> str:
    match = re.fullmatch(r"JP(\d+)", area_id)
    if match and 1 <= int(match.group(1)) <= len(PREFECTURES):
        return f"{PREFECTURES[int(match.group(1)) - 1]}({area_id})"
    return area_id


def _station_ids(xml_text: str) -> set[str]:
    return {station.findtext("id") for station in ET.fromstring(xml_text).iter("station")}


def _station_areas(xml_text: str) -> dict[str, tuple[str, str]]:
    return {
        station.findtext("id"): (station.findtext("name") or "", station.findtext("area_id") or "")
        for station in ET.fromstring(xml_text).iter("station")
    }


def _check_radiko(station_id: str) -> str | None:
    if station_id == "JOAB":
        raise StationError(NHK_RADIO2_MESSAGE)

    # 通信の失敗は「確認できなかった」だけなので録音は妨げない
    try:
        match = AREA_RE.search(fetch_text(AREA_URL))
        if not match:
            raise ValueError("現在のエリアを判定できませんでした")
        area = match.group(1)
        available = None if area == "OUT" else _station_ids(fetch_text(AREA_STATIONS_URL.format(area=area)))
    except Exception as exc:
        return f"局の確認をスキップしました（{type(exc).__name__}: {exc}）"

    if area == "OUT":
        raise StationError("日本国外からの接続と判定されたため、radikoを利用できません。")
    if station_id in available:
        return None

    try:
        known = _station_areas(fetch_text(FULL_STATIONS_URL))
    except Exception:
        known = None
    if known is None:
        raise StationError(
            f"局ID '{station_id}' は現在のエリア（{area_label(area)}）では聴取できません。"
        )
    if station_id not in known:
        raise StationError(
            f"局ID '{station_id}' はradikoの局一覧にありません。station_urlの局IDを確認してください。"
        )
    name, station_area = known[station_id]
    raise StationError(
        f"「{name}」({station_id}) は{area_label(station_area)}の局のため、"
        f"現在のエリア（{area_label(area)}）では録音できません"
        "（radikoの無料版は接続元エリアの局のみ聴取可能で、エリアフリーには未対応です）。"
    )


def check_station(program: Program) -> str | None:
    """録音できない局なら StationError を送出する。確認自体ができなかった場合は警告文を返す。"""
    url = urlparse(program.station_url)
    host = url.hostname or ""

    if host.endswith("nhk.or.jp"):
        if parse_qs(url.query).get("ch", [""])[0] == "r2":
            raise StationError(NHK_RADIO2_MESSAGE)
        return None

    if host.endswith("radiko.jp"):
        match = STATION_RE.search(program.station_url)
        if match:
            return _check_radiko(match.group(1))
    return None
