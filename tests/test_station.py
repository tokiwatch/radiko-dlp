import unittest
from unittest import mock

from radiru_dlp.config import Program
from radiru_dlp.station import (
    AREA_STATIONS_URL,
    AREA_URL,
    FULL_STATIONS_URL,
    StationError,
    area_label,
    check_station,
)

AREA_TOKYO = """document.write('<span class="JP13">TOKYO JAPAN</span>');"""
AREA_OUT = """document.write('<span class="OUT">OUT OF JAPAN</span>');"""
TOKYO_STATIONS = "<stations><station><id>TBS</id></station><station><id>JOAK</id></station></stations>"
FULL_STATIONS = """<region>
<stations><station><id>TBS</id><name>TBSラジオ</name><area_id>JP13</area_id></station></stations>
<stations><station><id>ABC</id><name>ABCラジオ</name><area_id>JP27</area_id></station></stations>
</region>"""


def program(url: str) -> Program:
    return Program(key="k", name="テスト番組", station_url=url, duration="00:10:00", output_dir="/tmp/x")


def fake_fetch(responses: dict[str, str | Exception]):
    def fetch(url, timeout=15):
        result = responses[url]
        if isinstance(result, Exception):
            raise result
        return result

    return fetch


RADIKO_OK = {
    AREA_URL: AREA_TOKYO,
    AREA_STATIONS_URL.format(area="JP13"): TOKYO_STATIONS,
    FULL_STATIONS_URL: FULL_STATIONS,
}


def check(url: str, responses: dict) -> str | None:
    with mock.patch("radiru_dlp.station.fetch_text", fake_fetch(responses)):
        return check_station(program(url))


class NhkRadio2Test(unittest.TestCase):
    def test_nhk_player_r2(self):
        with self.assertRaisesRegex(StationError, "NHKラジオ第2"):
            check("https://www.nhk.or.jp/radio/player/?ch=r2", {})

    def test_radiko_joab(self):
        with self.assertRaisesRegex(StationError, "NHKラジオ第2"):
            check("https://radiko.jp/#!/live/JOAB", {})

    def test_nhk_player_r1_and_fm_ok(self):
        self.assertIsNone(check("https://www.nhk.or.jp/radio/player/?ch=r1", {}))
        self.assertIsNone(check("https://www.nhk.or.jp/radio/player/?ch=fm", {}))


class RadikoAreaTest(unittest.TestCase):
    def test_in_area_station_ok(self):
        self.assertIsNone(check("https://radiko.jp/#!/live/TBS", RADIKO_OK))

    def test_other_area_station(self):
        with self.assertRaises(StationError) as ctx:
            check("https://radiko.jp/#!/live/ABC", RADIKO_OK)
        message = str(ctx.exception)
        self.assertIn("ABCラジオ", message)
        self.assertIn("大阪府(JP27)", message)
        self.assertIn("東京都(JP13)", message)

    def test_unknown_station(self):
        with self.assertRaisesRegex(StationError, "局一覧にありません"):
            check("https://radiko.jp/#!/live/NOSUCH", RADIKO_OK)

    def test_outside_japan(self):
        with self.assertRaisesRegex(StationError, "日本国外"):
            check("https://radiko.jp/#!/live/TBS", {AREA_URL: AREA_OUT})

    def test_full_list_unavailable_still_reports_unavailable(self):
        responses = {**RADIKO_OK, FULL_STATIONS_URL: OSError("down")}
        with self.assertRaisesRegex(StationError, "聴取できません"):
            check("https://radiko.jp/#!/live/ABC", responses)


class NetworkFailureTest(unittest.TestCase):
    def test_network_error_skips_check_with_warning(self):
        warning = check("https://radiko.jp/#!/live/ABC", {AREA_URL: OSError("timed out")})
        self.assertIn("スキップ", warning)

    def test_unparseable_area_skips_check(self):
        warning = check("https://radiko.jp/#!/live/TBS", {AREA_URL: "<html>"})
        self.assertIn("スキップ", warning)

    def test_other_urls_are_not_checked(self):
        self.assertIsNone(check("https://example.com/stream", {}))


class AreaLabelTest(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(area_label("JP1"), "北海道(JP1)")
        self.assertEqual(area_label("JP47"), "沖縄県(JP47)")
        self.assertEqual(area_label("JP99"), "JP99")
        self.assertEqual(area_label("OUT"), "OUT")


if __name__ == "__main__":
    unittest.main()
