import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


status = load_module("syz_campaign_status", "scripts/syz_campaign_status.py")
archive_crash = load_module("archive_crash", "scripts/archive_crash.py")


class StatusTests(unittest.TestCase):
    def test_parse_latest_stats_with_focus_area(self):
        parsed = status.parse_latest_stats(
            "2026/09/30 12:00:00 candidates=0 corpus=40 corpus [xfrm]=7 "
            "coverage=900 exec total=1200 (80/sec) pending=0 reproducing=0\n"
        )
        self.assertEqual(parsed["executions"], 1200)
        self.assertEqual(parsed["rate"], 80)
        self.assertEqual(parsed["focused_corpus"], {"xfrm": 7})

    def test_snapshot_scopes_manager_and_qemu_to_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workdir = root / "workdir"
            crashes = workdir / "crashes" / "abc123"
            crashes.mkdir(parents=True)
            (crashes / "description").write_text("BUG: KASAN test\n")
            (workdir / "corpus.db").write_bytes(b"corpus")
            kernel = root / "bzImage"
            kernel.write_bytes(b"kernel")
            config = root / "manager.cfg"
            config.write_text(json.dumps({
                "workdir": str(workdir),
                "vm": {"count": 1, "kernel": str(kernel)},
            }))
            log = root / "manager.log"
            log.write_text(
                "2026/09/30 12:00:00 candidates=0 corpus=40 corpus [xfrm]=7 "
                "coverage=900 exec total=1200 (80/sec) pending=0 reproducing=0\n"
            )
            os.utime(log, None)
            proc = root / "proc"
            manager = proc / "100"
            guest = proc / "101"
            manager.mkdir(parents=True)
            guest.mkdir(parents=True)
            (manager / "cmdline").write_bytes(
                f"/opt/syz-manager\0-config={config}\0".encode()
            )
            (guest / "cmdline").write_bytes(
                f"/usr/bin/qemu-system-x86_64\0-kernel\0{kernel}\0".encode()
            )
            pid_file = root / "manager.pid"
            pid_file.write_text("100\n")

            snapshot = status.build_snapshot(
                config, log, pid_file, proc, stale_after=600
            )
            self.assertEqual(snapshot["manager_pid"], 100)
            self.assertEqual(snapshot["guest_pids"], [101])
            self.assertEqual(snapshot["statistics"]["coverage"], 900)
            self.assertEqual(len(snapshot["crash_buckets"]), 1)
            self.assertEqual(snapshot["issues"], ["crash_buckets_present"])


class ArchiveTests(unittest.TestCase):
    def test_archive_is_additive_and_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bucket = root / "workdir" / "crashes" / "bucket1"
            bucket.mkdir(parents=True)
            (bucket / "description").write_text("BUG: KASAN example\n")
            (bucket / "log0").write_bytes(b"report")
            output = root / "evidence" / "bucket1"

            manifest = archive_crash.archive(root / "workdir", "bucket1", output)
            self.assertEqual(len(manifest["files"]), 2)
            self.assertTrue((output / "manifest.json").is_file())
            self.assertTrue((output / "SHA256SUMS").is_file())
            self.assertEqual((bucket / "log0").read_bytes(), b"report")
            with self.assertRaises(FileExistsError):
                archive_crash.archive(root / "workdir", "bucket1", output)

    def test_archive_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                archive_crash.archive(Path(temp), "../bucket", Path(temp) / "out")

    def test_archive_rejects_output_in_live_crash_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bucket = root / "workdir" / "crashes" / "bucket1"
            bucket.mkdir(parents=True)
            (bucket / "description").write_text("BUG: example\n")
            with self.assertRaises(ValueError):
                archive_crash.archive(
                    root / "workdir", "bucket1", bucket / "evidence"
                )


if __name__ == "__main__":
    unittest.main()
