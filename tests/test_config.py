import os
import stat
import tempfile
import unittest
from pathlib import Path

from radiko_dlp.config import (
    DEFAULT_FFMPEG,
    DEFAULT_YT_DLP,
    ConfigError,
    load_config,
    resolve_tool,
)

PROGRAM = """
[[programs]]
key = "k"
name = "n"
station_url = "https://radiko.jp/#!/live/TBS"
duration = "00:10:00"
output_dir = "/tmp/x"
"""


def load(text: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.toml"
        path.write_text(text, encoding="utf-8")
        return load_config(path)


class ToolsConfigTest(unittest.TestCase):
    def test_defaults_when_tools_omitted(self):
        config = load(PROGRAM)
        self.assertEqual(config.yt_dlp, DEFAULT_YT_DLP)
        self.assertEqual(config.ffmpeg, DEFAULT_FFMPEG)

    def test_override_and_partial(self):
        config = load('[tools]\nyt_dlp = "/opt/bin/yt-dlp"\n' + PROGRAM)
        self.assertEqual(config.yt_dlp, "/opt/bin/yt-dlp")
        self.assertEqual(config.ffmpeg, DEFAULT_FFMPEG)

    def test_tilde_is_expanded(self):
        config = load('[tools]\nffmpeg = "~/bin/ffmpeg"\n' + PROGRAM)
        self.assertEqual(config.ffmpeg, os.path.expanduser("~/bin/ffmpeg"))

    def test_unknown_key_rejected(self):
        with self.assertRaisesRegex(ConfigError, "未知の項目"):
            load('[tools]\nyt-dlp = "/x"\n' + PROGRAM)

    def test_non_string_rejected(self):
        with self.assertRaisesRegex(ConfigError, "空でない文字列"):
            load("[tools]\nffmpeg = 1\n" + PROGRAM)
        with self.assertRaisesRegex(ConfigError, "空でない文字列"):
            load('[tools]\nffmpeg = ""\n' + PROGRAM)

    def test_invalid_toml_is_config_error(self):
        with self.assertRaisesRegex(ConfigError, "書式が正しくありません"):
            load("[[programs]\nkey = ")


class MissingConfigTest(unittest.TestCase):
    def test_hint_to_copy_example(self):
        with self.assertRaisesRegex(ConfigError, "config.example.toml"):
            load_config(Path("/no/such/config.toml"))


class ResolveToolTest(unittest.TestCase):
    def test_executable_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "tool"
            exe.write_text("#!/bin/sh\n")
            exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
            self.assertEqual(resolve_tool("yt-dlp", str(exe)), str(exe))

    def test_command_name_is_searched_on_path(self):
        self.assertTrue(resolve_tool("sh", "sh").endswith("/sh"))

    def test_missing_or_non_executable(self):
        with self.assertRaisesRegex(ConfigError, "--yt-dlp"):
            resolve_tool("yt-dlp", "/no/such/yt-dlp")
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain"
            plain.write_text("x")
            with self.assertRaises(ConfigError):
                resolve_tool("ffmpeg", str(plain))


if __name__ == "__main__":
    unittest.main()
