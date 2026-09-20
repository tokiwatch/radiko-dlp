import contextlib
import importlib.machinery
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_script(name: str, filename: str):
    """拡張子なしの実行ファイルをモジュールとして読み込む。"""
    path = Path(__file__).resolve().parent.parent / filename
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


radiko_cron = load_script("radiko_cron", "radiko-cron")

CONFIG = """
[[programs]]
key = "k"
name = "n"
station_url = "https://radiko.jp/#!/live/TBS"
duration = "00:10:00"
schedule = "0 12 * * 1"
output_dir = "/tmp/x"
"""


def run_main_full(existing, *args: str, run_error=None):
    """run_main と同じだが、標準出力も含めて辞書で返す。"""
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.toml"
        config.write_text(CONFIG)
        if callable(existing):
            existing = existing(str(config.resolve()))
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(radiko_cron, "current_crontab", return_value=existing), \
                mock.patch.object(radiko_cron.subprocess, "run", side_effect=run_error) as run, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = radiko_cron.main(["--config", str(config), *args])
        return {
            "code": code, "stdout": stdout.getvalue(), "stderr": stderr.getvalue(),
            "written": run.call_args.kwargs["input"] if run.called else None,
            "config": str(config.resolve()),
        }


def run_main(existing, *args: str, run_error=None):
    """実際のcrontabには触れず、(終了コード, 書き込まれた内容 or None, stderr, 設定ファイルのパス) を返す。

    existing は crontab の内容、または設定ファイルのパスを受け取ってその内容を返す関数。
    """
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "config.toml"
        config.write_text(CONFIG)
        if callable(existing):
            existing = existing(str(config.resolve()))
        stderr = io.StringIO()
        with mock.patch.object(radiko_cron, "current_crontab", return_value=existing), \
                mock.patch.object(radiko_cron.subprocess, "run", side_effect=run_error) as run, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = radiko_cron.main(["--config", str(config), *args])
        written = run.call_args.kwargs["input"] if run.called else None
        return code, written, stderr.getvalue(), str(config.resolve())


class RegisteredConfigTest(unittest.TestCase):
    def test_none_when_absent(self):
        self.assertIsNone(radiko_cron.registered_config(""))
        self.assertIsNone(radiko_cron.registered_config("0 3 * * * /usr/bin/backup\n"))

    def test_reads_config_path_from_block(self):
        text = f"{radiko_cron.MARKER_BEGIN}\n# config: /a/config.toml\n0 1 * * * x\n{radiko_cron.MARKER_END}\n"
        self.assertEqual(radiko_cron.registered_config(text), "/a/config.toml")

    def test_ignores_config_line_outside_block(self):
        text = f"# config: /outside\n{radiko_cron.MARKER_BEGIN}\n{radiko_cron.MARKER_END}\n"
        self.assertIsNone(radiko_cron.registered_config(text))


class ApplyGuardTest(unittest.TestCase):
    def other_block(self):
        return f"{radiko_cron.MARKER_BEGIN}\n# config: /other/config.toml\n0 1 * * * x\n{radiko_cron.MARKER_END}\n"

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
                    f"{radiko_cron.MARKER_BEGIN}\n# config: {config}\n0 1 * * * old-entry\n{radiko_cron.MARKER_END}\n"
                    "5 5 * * * /usr/bin/after\n")

        code, written, _, config = run_main(existing, "--apply")
        self.assertEqual(code, 0)
        self.assertIn("0 3 * * * /usr/bin/backup", written)
        self.assertIn("5 5 * * * /usr/bin/after", written)
        self.assertNotIn("old-entry", written)
        self.assertEqual(written.count(radiko_cron.MARKER_BEGIN), 1)
        self.assertIn(f"# config: {config}", written)

    def test_force_keeps_entries_outside_block(self):
        code, written, _, _ = run_main("0 3 * * * /usr/bin/backup\n" + self.other_block(), "--apply", "--force")
        self.assertEqual(code, 0)
        self.assertIn("0 3 * * * /usr/bin/backup", written)


class ErrorHandlingTest(unittest.TestCase):
    def test_block_without_end_marker_is_reported(self):
        broken = f"{radiko_cron.MARKER_BEGIN}\n0 1 * * * x\n"
        code, written, stderr, _ = run_main(broken, "--apply")
        self.assertEqual(code, 1)
        self.assertIsNone(written)
        self.assertIn(radiko_cron.MARKER_END, stderr)

    def test_end_marker_before_begin_is_treated_as_missing(self):
        broken = f"{radiko_cron.MARKER_END}\n{radiko_cron.MARKER_BEGIN}\n"
        with self.assertRaises(radiko_cron.CrontabError):
            radiko_cron.merge_crontab(broken, "x\n")

    def test_crontab_rejecting_input_is_reported(self):
        error = radiko_cron.subprocess.CalledProcessError(1, "crontab")
        code, _, stderr, _ = run_main("", "--apply", run_error=error)
        self.assertEqual(code, 1)
        self.assertIn("schedule", stderr)


class DryRunTest(unittest.TestCase):
    def test_dry_run_shows_block_and_diff_and_writes_nothing(self):
        result = run_main_full("0 3 * * * /usr/bin/backup\n", "--dry-run")
        self.assertEqual(result["code"], 0)
        self.assertIsNone(result["written"])
        out = result["stdout"]
        self.assertIn("予約 1 件", out)
        self.assertIn(radiko_cron.MARKER_BEGIN, out)
        self.assertIn("0 12 * * 1 ", out)
        self.assertIn("+# BEGIN radiko-dlp", out)
        self.assertNotIn("-0 3 * * * /usr/bin/backup", out)

    def test_dry_run_takes_precedence_over_apply(self):
        result = run_main_full("", "--apply", "--dry-run")
        self.assertEqual(result["code"], 0)
        self.assertIsNone(result["written"])

    def test_dry_run_reports_no_difference_when_already_registered(self):
        def existing(config):
            block = radiko_cron.build_block(
                radiko_cron.load_config(Path(config)),
                Path(radiko_cron.__file__).resolve().parent / "radiko-record", Path(config))
            return block
        result = run_main_full(existing, "--dry-run")
        self.assertIn("差分: なし", result["stdout"])
        self.assertNotIn("+++", result["stdout"])

    def test_dry_run_shows_changed_line(self):
        def existing(config):
            return (f"{radiko_cron.MARKER_BEGIN}\n# config: {config}\n"
                    f"0 9 * * 1 /old/radiko-record --config {config} k\n{radiko_cron.MARKER_END}\n")
        out = run_main_full(existing, "--dry-run")["stdout"]
        self.assertIn("-0 9 * * 1 /old/radiko-record", out)
        self.assertIn("+0 12 * * 1 ", out)

    def test_dry_run_with_other_config_only_warns(self):
        other = (f"{radiko_cron.MARKER_BEGIN}\n# config: /other/config.toml\n0 1 * * * x\n"
                 f"{radiko_cron.MARKER_END}\n")
        result = run_main_full(other, "--apply", "--dry-run")
        self.assertEqual(result["code"], 0)
        self.assertIsNone(result["written"])
        self.assertIn("警告", result["stderr"])
        self.assertIn("-0 1 * * * x", result["stdout"])


if __name__ == "__main__":
    unittest.main()
