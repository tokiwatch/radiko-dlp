import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import manage_cron

CONFIG = """
[[programs]]
key = "k"
name = "n"
station_url = "https://radiko.jp/#!/live/TBS"
duration = "00:10:00"
schedule = "0 12 * * 1"
output_dir = "/tmp/x"
"""


def run_main(existing, *args: str):
    """実際のcrontabには触れず、(終了コード, 書き込まれた内容 or None, stderr, 設定ファイルのパス) を返す。

    existing は crontab の内容、または設定ファイルのパスを受け取ってその内容を返す関数。
    """
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.toml"
        config.write_text(CONFIG)
        if callable(existing):
            existing = existing(str(config.resolve()))
        stderr = io.StringIO()
        with mock.patch.object(manage_cron, "current_crontab", return_value=existing), \
                mock.patch.object(manage_cron.subprocess, "run") as run, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = manage_cron.main(["--config", str(config), *args])
        written = run.call_args.kwargs["input"] if run.called else None
        return code, written, stderr.getvalue(), str(config.resolve())


class RegisteredConfigTest(unittest.TestCase):
    def test_none_when_absent(self):
        self.assertIsNone(manage_cron.registered_config(""))
        self.assertIsNone(manage_cron.registered_config("0 3 * * * /usr/bin/backup\n"))

    def test_reads_config_path_from_block(self):
        text = f"{manage_cron.MARKER_BEGIN}\n# config: /a/config.toml\n0 1 * * * x\n{manage_cron.MARKER_END}\n"
        self.assertEqual(manage_cron.registered_config(text), "/a/config.toml")

    def test_ignores_config_line_outside_block(self):
        text = f"# config: /outside\n{manage_cron.MARKER_BEGIN}\n{manage_cron.MARKER_END}\n"
        self.assertIsNone(manage_cron.registered_config(text))


class ApplyGuardTest(unittest.TestCase):
    def other_block(self):
        return f"{manage_cron.MARKER_BEGIN}\n# config: /other/config.toml\n0 1 * * * x\n{manage_cron.MARKER_END}\n"

    def test_fresh_crontab_is_applied_and_records_config(self):
        code, written, _, config = run_main("", "--apply")
        self.assertEqual(code, 0)
        self.assertIn(f"# config: {config}", written)

    def test_other_config_is_refused_without_force(self):
        code, written, stderr, _ = run_main(self.other_block(), "--apply")
        self.assertEqual(code, 1)
        self.assertIsNone(written)
        self.assertIn("/other/config.toml", stderr)
        self.assertIn("--force", stderr)

    def test_force_overrides(self):
        code, written, _, _ = run_main(self.other_block(), "--apply", "--force")
        self.assertEqual(code, 0)
        self.assertNotIn("/other/config.toml", written)

    def test_preview_only_warns(self):
        code, written, stderr, _ = run_main(self.other_block())
        self.assertEqual(code, 0)
        self.assertIsNone(written)
        self.assertIn("警告", stderr)

    def test_same_config_is_reapplied_without_force_and_other_entries_kept(self):
        def existing(config: str) -> str:
            return ("0 3 * * * /usr/bin/backup\n"
                    f"{manage_cron.MARKER_BEGIN}\n# config: {config}\n0 1 * * * old-entry\n{manage_cron.MARKER_END}\n"
                    "5 5 * * * /usr/bin/after\n")

        code, written, _, config = run_main(existing, "--apply")
        self.assertEqual(code, 0)
        self.assertIn("0 3 * * * /usr/bin/backup", written)
        self.assertIn("5 5 * * * /usr/bin/after", written)
        self.assertNotIn("old-entry", written)
        self.assertEqual(written.count(manage_cron.MARKER_BEGIN), 1)
        self.assertIn(f"# config: {config}", written)

    def test_force_keeps_entries_outside_block(self):
        code, written, _, _ = run_main("0 3 * * * /usr/bin/backup\n" + self.other_block(), "--apply", "--force")
        self.assertEqual(code, 0)
        self.assertIn("0 3 * * * /usr/bin/backup", written)


if __name__ == "__main__":
    unittest.main()
