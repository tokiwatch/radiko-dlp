import gzip
import unittest
from datetime import datetime, timedelta

from radiru_dlp.guide import (
    JST,
    GuideError,
    decode_body,
    parse_guide,
    pick_program,
    sanitize_filename_part,
    station_id_from_url,
)

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<radiko><stations><station id="JOAK-FM"><name>NHK FM（東京）</name><progs>
<prog id="1" ft="20260920072000" to="20260920081000" dur="3000">
  <title>ビバ！合唱</title><pfm>戸﨑文葉</pfm><info></info><desc></desc><url>https://example.com/a/</url>
</prog>
<prog id="2" ft="20260920081000" to="20260920090000" dur="3000">
  <title>現代の音楽　最近の公演から　２０２６年度（１）</title>
  <pfm>白石美雪/杉山洋一</pfm>
  <info><![CDATA[白石美雪<br><br>「超新星」<br>作曲：チェ]]></info>
  <desc></desc><url>https://example.com/b/</url>
</prog>
<prog id="3" ft="20260920090000" to="20260920105500" dur="6900">
  <title>名演奏ライブラリー</title><pfm></pfm><info></info><desc>説明のみ</desc><url></url>
</prog>
</progs></station></stations></radiko>
"""


def at(hhmm: str) -> datetime:
    return datetime(2026, 9, 20, int(hhmm[:2]), int(hhmm[2:]), tzinfo=JST)


class ParseGuideTest(unittest.TestCase):
    def test_parse_fields(self):
        programs = parse_guide(SAMPLE_XML)
        self.assertEqual(len(programs), 3)
        gendai = programs[1]
        self.assertEqual(gendai.start, at("0810"))
        self.assertEqual(gendai.end, at("0900"))
        self.assertEqual(gendai.performers, "白石美雪/杉山洋一")
        self.assertEqual(gendai.description, "白石美雪\n\n「超新星」\n作曲：チェ")

    def test_description_falls_back_to_desc(self):
        self.assertEqual(parse_guide(SAMPLE_XML)[2].description, "説明のみ")


class DecodeBodyTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(decode_body("現代の音楽".encode()), "現代の音楽")

    def test_gzip(self):
        self.assertEqual(decode_body(gzip.compress("現代の音楽".encode())), "現代の音楽")

    def test_truncated_gzip_raises(self):
        with self.assertRaises(EOFError):
            decode_body(gzip.compress(b"x" * 1000)[:20])


class PickProgramTest(unittest.TestCase):
    def setUp(self):
        self.programs = parse_guide(SAMPLE_XML)

    def test_start_exactly_at_program_start(self):
        picked = pick_program(self.programs, at("0810"), 51 * 60)
        self.assertIn("現代の音楽", picked.title)

    def test_start_slightly_before_program(self):
        picked = pick_program(self.programs, at("0810") - timedelta(seconds=10), 51 * 60)
        self.assertIn("現代の音楽", picked.title)

    def test_no_overlap_returns_none(self):
        self.assertIsNone(pick_program(self.programs, at("2000"), 3000))


class SanitizeTest(unittest.TestCase):
    def test_nfkc_and_symbols(self):
        self.assertEqual(
            sanitize_filename_part("現代の音楽　２０２６年度／本選：（１）"),
            "現代の音楽 2026年度_本選_(1)",
        )

    def test_truncates_by_bytes(self):
        result = sanitize_filename_part("あ" * 100, max_bytes=30)
        self.assertEqual(result, "あ" * 10)

    def test_strips_trailing_dots_and_spaces(self):
        self.assertEqual(sanitize_filename_part(" タイトル. "), "タイトル")


class StationIdTest(unittest.TestCase):
    def test_from_url(self):
        self.assertEqual(station_id_from_url("https://radiko.jp/#!/live/JOAK-FM"), "JOAK-FM")

    def test_invalid(self):
        with self.assertRaises(GuideError):
            station_id_from_url("https://example.com/")


if __name__ == "__main__":
    unittest.main()
