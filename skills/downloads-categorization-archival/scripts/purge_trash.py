#!/usr/bin/env python3
"""Permanently delete staged files that have sat in trash/<run-date>/
longer than the grace period. Logs every permanent deletion before it
happens.

Usage:
    python purge_trash.py [--state-dir DIR] [--grace-days 14] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _common import append_log_entries, load_json, state_dir, utc_now_iso


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--grace-days", type=int, default=14)
    ap.add_argument("--dry-run", action="store_true",
                     help="Report what would be purged without deleting anything.")
    args = ap.parse_args()

    state = state_dir(args.state_dir)
    trash = state / "trash"
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.grace_days)

    entries = []
    eligible_dirs = 0
    for run_dir in sorted(trash.iterdir()):
        if not run_dir.is_dir():
            continue
        try:
            run_date = datetime.strptime(run_dir.name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue  # not a run-dated folder, leave it alone
        if run_date >= cutoff:
            continue  # still inside the grace period

        eligible_dirs += 1
        # Each staged file has a sidecar <name>.meta.json (written by
        # stage_for_deletion.py) carrying the SharePoint evidence it was
        # verified against — surface that in the deletion log entry so the
        # audit trail actually shows *why* each file was safe to remove.
        staged_files = [
            p for p in run_dir.rglob("*")
            if p.is_file() and not p.name.endswith(".meta.json")
        ]
        for f in staged_files:
            meta_path = f.with_name(f.name + ".meta.json")
            meta = load_json(meta_path, {})
            entry = {
                "run_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "path": meta.get("original_relative_path", str(f.relative_to(run_dir))),
                "action": "purged",
                "detail": f"staged on {run_dir.name} ({meta.get('action', 'unknown reason')}), "
                          f"purged after {args.grace_days}-day grace period",
                "logged_at": utc_now_iso(),
            }
            if meta.get("sharepoint_url"):
                entry["sharepoint_url"] = meta["sharepoint_url"]
            entries.append(entry)

        if not args.dry_run:
            shutil.rmtree(run_dir)

    if entries and not args.dry_run:
        append_log_entries(entries, state)

    verb = "would purge" if args.dry_run else "purged"
    print(f"{verb} {len(entries)} file(s) across {eligible_dirs} "
          f"staged run folder(s) older than {args.grace_days} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
