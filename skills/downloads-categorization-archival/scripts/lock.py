#!/usr/bin/env python3
"""A single run lock so a manually-triggered run and the weekly scheduled
run can't overlap and double-process (or double-upload/double-delete) the
same files. There's no supervisor process here to clean up after a crash,
so a stale lock (older than the threshold in _common.LOCK_STALE_SECONDS)
is auto-reclaimed rather than left to block every future run forever.

Usage:
    python lock.py acquire [--state-dir DIR]   # exit 0 if acquired, 1 if held by another run
    python lock.py release [--state-dir DIR]   # always exit 0

Call `acquire` as the very first step of any run (attended or unattended).
If it exits 1, stop — do not proceed with scanning/categorizing/moving
anything. Call `release` at the end of the run, including on early exit
(e.g. the SharePoint connector isn't available).
"""
from __future__ import annotations

import argparse
import sys

from _common import acquire_lock, release_lock, state_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["acquire", "release"])
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args()

    state = state_dir(args.state_dir)

    if args.mode == "acquire":
        ok, message = acquire_lock(state)
        print(message)
        return 0 if ok else 1

    release_lock(state)
    print("lock released")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
