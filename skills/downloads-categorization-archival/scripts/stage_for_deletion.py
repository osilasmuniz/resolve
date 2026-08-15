#!/usr/bin/env python3
"""Move a file out of Downloads into the local trash staging area,
preserving its relative path, and log the action. This is the ONLY way
files should leave Downloads in this skill — never delete or move a
Downloads file with raw shell commands, so that every relocation is
atomic, collision-checked, and carries the SharePoint evidence it was
verified against.

Usage:
    python stage_for_deletion.py <downloads-path> <relative-file-path> \\
        --action staged_duplicate --category "Tax Documents" \\
        --sharepoint-url URL [--detail TEXT] [--state-dir DIR]

--action must be one of: staged_duplicate, uploaded_allocate_properly
(these are the two SKILL.md paths that lead here — a confirmed SharePoint
duplicate, or a file successfully uploaded to Allocate Properly).

--sharepoint-url is required: this script is the safety gate for the one
irreversible-feeling action in the whole skill, so it refuses to stage a
file without the evidence of *why* it's safe to remove locally. That
evidence is written alongside the staged file (a `.meta.json` sidecar) so
purge_trash.py can include it in the final deletion log entry.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from _common import append_log_entries, save_json, state_dir, today_run_date

VALID_ACTIONS = {"staged_duplicate", "uploaded_allocate_properly"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("downloads_path")
    ap.add_argument("relative_file_path")
    ap.add_argument("--action", required=True, choices=sorted(VALID_ACTIONS))
    ap.add_argument("--category", default="Other/Unclear")
    ap.add_argument("--sharepoint-url", required=True)
    ap.add_argument("--detail", default=None)
    ap.add_argument("--state-dir", default=None)
    args = ap.parse_args()

    downloads_path = Path(args.downloads_path).expanduser()
    src = downloads_path / args.relative_file_path
    if not src.is_file() or src.is_symlink():
        print(f"error: {src} is not a plain file (already moved? symlink? wrong path?)", file=sys.stderr)
        return 1

    state = state_dir(args.state_dir)
    run_date = today_run_date()
    dest = state / "trash" / run_date / args.relative_file_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        # Extremely unlikely (same relative path staged twice same day) —
        # don't silently overwrite a previously staged file.
        print(f"error: {dest} already exists in today's trash, refusing to overwrite", file=sys.stderr)
        return 1

    shutil.move(str(src), str(dest))

    meta = {
        "run_date": run_date,
        "original_relative_path": args.relative_file_path,
        "category": args.category,
        "action": args.action,
        "sharepoint_url": args.sharepoint_url,
        "detail": args.detail,
    }
    meta_path = dest.with_name(dest.name + ".meta.json")
    save_json(meta_path, meta)

    entry = {
        "run_date": run_date,
        "path": args.relative_file_path,
        "category": args.category,
        "action": args.action,
        "staged_at": str(dest),
        "sharepoint_url": args.sharepoint_url,
    }
    if args.detail:
        entry["detail"] = args.detail

    append_log_entries([entry], state)
    print(f"staged: {src} -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
