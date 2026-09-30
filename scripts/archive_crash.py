#!/usr/bin/env python3
"""Archive one syzkaller crash bucket with checksums and a manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive(workdir: Path, bucket: str, output: Path) -> dict[str, object]:
    if not bucket or Path(bucket).name != bucket or bucket in {".", ".."}:
        raise ValueError("bucket must be one directory name")

    crashes = (workdir.resolve() / "crashes").resolve()
    source = crashes / bucket
    if source.is_symlink() or not source.is_dir() or source.resolve().parent != crashes:
        raise ValueError(f"crash bucket does not exist: {bucket}")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("crash bucket contains a symbolic link")

    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if output == crashes or crashes in output.parents:
        raise ValueError("output must be outside the live crashes directory")
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copytree(source, output)
        files = []
        for path in sorted(item for item in output.rglob("*") if item.is_file()):
            relative = path.relative_to(output).as_posix()
            files.append({
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
        manifest = {
            "archived_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": str(source),
            "bucket": bucket,
            "files": files,
        }
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output / "SHA256SUMS").write_text(
            "".join(f"{item['sha256']}  {item['path']}\n" for item in files),
            encoding="utf-8",
        )
        return manifest
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--workdir", required=True, type=Path,
                        help="syzkaller work directory")
    result.add_argument("--bucket", required=True,
                        help="crash bucket directory name")
    result.add_argument("--output", required=True, type=Path,
                        help="new evidence directory; must not exist")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = archive(args.workdir, args.bucket, args.output)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"archived {len(manifest['files'])} files to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
