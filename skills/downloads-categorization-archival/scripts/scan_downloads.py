#!/usr/bin/env python3
"""Recursively scan a Downloads folder and diff it against the manifest
cache from the last run, so the caller only has to think about files that
are actually new or changed.

Usage:
    python scan_downloads.py <downloads-path> [--state-dir DIR] [--commit]

Prints a JSON object to stdout:
    {
      "new": [ {path, size, mtime, sha256}, ... ],
      "changed": [ ... ],
      "unchanged_count": N,
      "removed_count": N   # were in the cache, no longer on disk
    }

By default this does NOT mutate manifest-cache.json — pass --commit once
the caller has actually finished processing this run's new/changed files,
so a crash mid-run doesn't cause a file to be silently skipped next time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from _common import is_noise, load_json, save_json, state_dir

HASH_CHUNK = 1024 * 1024


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(downloads_path: Path) -> dict:
    """Walk the tree with followlinks=False. Downloads folders don't
    normally contain meaningful symlinks, and following them risks an
    infinite loop on a cyclic symlink or silently hashing/reporting
    content that actually lives outside Downloads — better to just skip
    them (a symlink pointing to something worth keeping is a Downloads
    hygiene problem Silas should notice on his own, not something this
    skill should traverse into)."""
    files = {}
    for root, dirnames, filenames in os.walk(downloads_path, followlinks=False):
        root_path = Path(root)
        for name in filenames:
            p = root_path / name
            if p.is_symlink() or is_noise(name):
                continue
            if not p.is_file():
                continue
            rel = str(p.relative_to(downloads_path))
            stat = p.stat()
            files[rel] = {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "sha256": sha256_of(p),
            }
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("downloads_path")
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--commit", action="store_true",
                     help="Persist the fresh manifest as this run's cache.")
    args = ap.parse_args()

    downloads_path = Path(args.downloads_path).expanduser()
    if not downloads_path.is_dir():
        print(f"error: {downloads_path} is not a directory", file=sys.stderr)
        return 1

    state = state_dir(args.state_dir)
    cache_path = state / "manifest-cache.json"
    cache = load_json(cache_path, {})

    current = scan(downloads_path)

    new_files, changed_files = [], []
    for rel, meta in current.items():
        prior = cache.get(rel)
        if prior is None:
            new_files.append({"path": rel, **meta})
        elif prior.get("sha256") != meta["sha256"]:
            changed_files.append({"path": rel, **meta})

    unchanged_count = len(current) - len(new_files) - len(changed_files)
    removed_count = len(set(cache) - set(current))

    result = {
        "downloads_path": str(downloads_path),
        "new": new_files,
        "changed": changed_files,
        "unchanged_count": unchanged_count,
        "removed_count": removed_count,
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    if args.commit:
        save_json(cache_path, current)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
