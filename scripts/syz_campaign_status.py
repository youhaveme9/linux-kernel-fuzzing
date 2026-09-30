#!/usr/bin/env python3
"""Collect a deterministic, read-only syzkaller campaign snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable


STAT_PATTERNS = {
    "candidates": re.compile(r"\bcandidates=(\d+)"),
    "corpus": re.compile(r"\bcorpus=(\d+)"),
    "coverage": re.compile(r"\bcoverage=(\d+)"),
    "executions": re.compile(r"\bexec total=(\d+)"),
    "pending": re.compile(r"\bpending=(\d+)"),
    "reproducing": re.compile(r"\breproducing=(\d+)"),
}
RATE_RE = re.compile(r"\((\d+)/(sec|min)\)")
FOCUS_RE = re.compile(r"corpus \[([^\]]+)\]=(\d+)")
TIMESTAMP_RE = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")


def read_tail(path: Path, max_bytes: int = 2 * 1024 * 1024) -> str:
    """Read at most max_bytes from the end of a text file."""
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - max_bytes))
        data = stream.read()
    return data.decode("utf-8", errors="replace")


def parse_latest_stats(text: str) -> dict[str, object]:
    """Parse the newest syz-manager periodic statistics line."""
    line = next(
        (candidate.strip() for candidate in reversed(text.splitlines())
         if "exec total=" in candidate),
        "",
    )
    if not line:
        return {}

    result: dict[str, object] = {"raw": line}
    timestamp = TIMESTAMP_RE.search(line)
    if timestamp:
        result["timestamp"] = timestamp.group(1)
    for name, pattern in STAT_PATTERNS.items():
        match = pattern.search(line)
        if match:
            result[name] = int(match.group(1))
    rate = RATE_RE.search(line)
    if rate:
        result["rate"] = int(rate.group(1))
        result["rate_unit"] = rate.group(2)
    result["focused_corpus"] = {
        name: int(value) for name, value in FOCUS_RE.findall(line)
    }
    return result


def iter_processes(proc_root: Path) -> Iterable[tuple[int, list[str]]]:
    """Yield process IDs and argv from a Linux procfs tree."""
    try:
        entries = proc_root.iterdir()
    except OSError:
        return
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        argv = [part.decode("utf-8", errors="replace")
                for part in raw.split(b"\0") if part]
        if argv:
            yield int(entry.name), argv


def _same_path(candidate: str, expected: Path) -> bool:
    try:
        return Path(candidate).resolve() == expected.resolve()
    except OSError:
        return candidate == str(expected)


def is_manager_for_config(argv: list[str], config: Path) -> bool:
    if not argv or "syz-manager" not in Path(argv[0]).name:
        return False
    for index, arg in enumerate(argv[1:]):
        if arg.startswith("-config=") and _same_path(arg.split("=", 1)[1], config):
            return True
        if arg == "-config" and index + 2 < len(argv):
            if _same_path(argv[index + 2], config):
                return True
    return False


def find_manager(config: Path, processes: list[tuple[int, list[str]]],
                 pid_file: Path | None) -> int | None:
    preferred: int | None = None
    if pid_file and pid_file.exists():
        try:
            preferred = int(pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            preferred = None
    for pid, argv in processes:
        if preferred == pid and is_manager_for_config(argv, config):
            return pid
    for pid, argv in processes:
        if is_manager_for_config(argv, config):
            return pid
    return None


def find_qemu_guests(kernel: Path | None,
                     processes: list[tuple[int, list[str]]]) -> list[int]:
    if kernel is None:
        return []
    result = []
    for pid, argv in processes:
        if not argv or "qemu-system" not in Path(argv[0]).name:
            continue
        if any(_same_path(arg, kernel) for arg in argv[1:]):
            result.append(pid)
    return sorted(result)


def crash_buckets(workdir: Path) -> list[dict[str, str]]:
    crashes = workdir / "crashes"
    result = []
    try:
        entries = sorted(crashes.iterdir(), key=lambda item: item.name)
    except OSError:
        return result
    for entry in entries:
        if not entry.is_dir():
            continue
        description = ""
        try:
            description = (entry / "description").read_text(
                encoding="utf-8", errors="replace").strip()
        except OSError:
            pass
        result.append({"name": entry.name, "description": description})
    return result


def build_snapshot(config_path: Path, log_path: Path,
                   pid_file: Path | None, proc_root: Path,
                   stale_after: int) -> dict[str, object]:
    config_path = config_path.resolve()
    log_path = log_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    workdir = Path(config["workdir"]).resolve()
    kernel_value = config.get("vm", {}).get("kernel")
    kernel = Path(kernel_value).resolve() if kernel_value else None
    expected_vms = int(config.get("vm", {}).get("count", 0))
    processes = list(iter_processes(proc_root))
    manager_pid = find_manager(config_path, processes, pid_file)
    guest_pids = find_qemu_guests(kernel, processes)
    buckets = crash_buckets(workdir)
    stats = parse_latest_stats(read_tail(log_path))

    issues = []
    if manager_pid is None:
        issues.append("manager_not_running")
    if expected_vms and len(guest_pids) != expected_vms:
        issues.append("guest_count_mismatch")
    if not stats:
        issues.append("no_periodic_stats")
    if buckets:
        issues.append("crash_buckets_present")
    log_age = max(0, int(dt.datetime.now().timestamp() - log_path.stat().st_mtime))
    if stale_after > 0 and log_age > stale_after:
        issues.append("manager_log_stale")

    corpus = workdir / "corpus.db"
    corpus_info: dict[str, object] = {"path": str(corpus), "exists": corpus.exists()}
    if corpus.exists():
        stat = corpus.stat()
        corpus_info.update({"size_bytes": stat.st_size, "mtime": stat.st_mtime})

    return {
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "config": str(config_path),
        "manager_log": str(log_path),
        "manager_log_age_seconds": log_age,
        "workdir": str(workdir),
        "kernel": str(kernel) if kernel else None,
        "manager_pid": manager_pid,
        "expected_guests": expected_vms,
        "guest_pids": guest_pids,
        "statistics": stats,
        "corpus_db": corpus_info,
        "crash_buckets": buckets,
        "issues": issues,
    }


def print_human(snapshot: dict[str, object]) -> None:
    stats = snapshot["statistics"]
    print(f"manager: {'running pid ' + str(snapshot['manager_pid']) if snapshot['manager_pid'] else 'not running'}")
    print(f"guests: {len(snapshot['guest_pids'])}/{snapshot['expected_guests']}")
    if stats:
        rate = f"{stats.get('rate', '?')}/{stats.get('rate_unit', '?')}"
        print(f"executions: {stats.get('executions', '?')} ({rate})")
        print(f"coverage: {stats.get('coverage', '?')}")
        print(f"corpus: {stats.get('corpus', '?')}")
        focused = stats.get("focused_corpus", {})
        if focused:
            print("focused corpus: " + ", ".join(
                f"{name}={value}" for name, value in sorted(focused.items())))
    print(f"crash buckets: {len(snapshot['crash_buckets'])}")
    issues = snapshot["issues"]
    print("issues: " + (", ".join(issues) if issues else "none"))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", required=True, type=Path,
                        help="syz-manager JSON configuration")
    result.add_argument("--log", required=True, type=Path,
                        help="syz-manager log")
    result.add_argument("--manager-pid-file", type=Path,
                        help="optional manager PID file")
    result.add_argument("--proc-root", type=Path, default=Path("/proc"),
                        help=argparse.SUPPRESS)
    result.add_argument("--stale-after", type=int, default=600,
                        help="report a stale log after this many seconds; 0 disables")
    result.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON")
    result.add_argument("--strict", action="store_true",
                        help="exit 1 when the snapshot contains an issue")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        snapshot = build_snapshot(args.config, args.log, args.manager_pid_file,
                                  args.proc_root, args.stale_after)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        print_human(snapshot)
    return 1 if args.strict and snapshot["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
