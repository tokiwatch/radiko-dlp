import tempfile
import unittest
from pathlib import Path

from radiko_dlp.config import Program
from radiko_dlp.recording import apply_test_mode, unique_path


def program(duration: str = "00:51:00") -> Program:
    return Program(key="k", name="n", station_url="https://radiko.jp/#!/live/TBS",
                   duration=duration, output_dir="~/Music/radio/k", schedule="10 8 * * 0")


class ApplyTestModeTest(unittest.TestCase):
    def test_shortens_duration_and_redirects_output(self):
        result = apply_test_mode(program())
        self.assertEqual(result.duration, "00:01:00")
        self.assertEqual(result.output_dir, str(Path("~/Music/radio/k").expanduser() / "test"))

    def test_keeps_shorter_duration(self):
        self.assertEqual(apply_test_mode(program("00:00:10")).duration, "00:00:10")

    def test_original_is_unchanged(self):
        original = program()
        apply_test_mode(original)
        self.assertEqual(original.duration, "00:51:00")
        self.assertEqual(original.output_dir, "~/Music/radio/k")


class UniquePathTest(unittest.TestCase):
    def test_free_name_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.m4a"
            self.assertEqual(unique_path(path), path)

    def test_existing_file_gets_numbered_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.m4a"
            path.write_text("x")
            self.assertEqual(unique_path(path), Path(tmp) / "a_2.m4a")
            (Path(tmp) / "a_2.m4a").write_text("x")
            self.assertEqual(unique_path(path), Path(tmp) / "a_3.m4a")
            self.assertEqual(path.read_text(), "x")


if __name__ == "__main__":
    unittest.main()
