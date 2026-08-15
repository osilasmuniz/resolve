#!/usr/bin/env python3
"""Append one or more structured log entries to log.jsonl and regenerate
the trimmed log-summary.md (last 8 runs only — see
references/token-and-memory-optimization.md for why the summary stays
small on purpose while the JSONL stays complete).

Usage:
    echo '{"path": "foo.pdf", "action": "staged_duplicate", ...}' | python append_log.py
    python append_log.py --entries entries.json   # a JSON array of entries

Each entry should include at least: run_date, path, category, action.
Recognized actions: scanned, categorized, matched_duplicate, staged_duplicate,
uploaded_allocate_properly, needs_review, purged.
"""
from __future__ import annotations

import argparse
import json
import sys

from _common import append_log_entries, state_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--entries", default=None,
                     help="Path to a JSON file containing an array of entries. "
                          "If omitted, reads a single JSON object (or array) from stdin.")
    args = ap.parse_args()

    if args.entries:
        with open(args.entries, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = json.load(sys.stdin)

    entries = payload if isinstance(payload, list) else [payload]

    state = state_dir(args.state_dir)
    append_log_entries(entries, state)
    print(f"appended {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}; "
          f"log-summary.md regenerated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
