"""Shared helpers for the downloads-categorization-archival scripts.

Kept deliberately small and dependency-free (stdlib only) so these scripts
run anywhere Python 3 runs, with no install step.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE_DIR = Path(os.environ.get(
    "DOWNLOADS_MAINTENANCE_STATE_DIR",
    str(Path.home() / ".downloads-maintenance"),
))

NOISE_NAMES = {".DS_Store", "desktop.ini", "Thumbs.db"}
NOISE_SUFFIXES = {".crdownload", ".part", ".tmp"}

MAX_SUMMARY_RUNS = 8

# The only action names any script/skill step should ever write to
# log.jsonl. Keeping this list here (rather than duplicated in prose across
# SKILL.md and references/*.md) is what keeps them from drifting apart.
KNOWN_ACTIONS = {
    "scanned",
    "categorized",
    "matched_duplicate",
    "staged_duplicate",
    "uploaded_allocate_properly",
    "needs_review",
    "purged",
}

# Actions that mean "this path is no longer awaiting a decision" and should
# clear it from needs-review.json if it's there.
RESOLVING_ACTIONS = {"matched_duplicate", "staged_duplicate", "uploaded_allocate_properly", "purged"}

LOCK_STALE_SECONDS = 2 * 60 * 60  # a lock older than this is assumed abandoned (crash), not active


def state_dir(explicit: str | None = None) -> Path:
    d = Path(explicit).expanduser() if explicit else DEFAULT_STATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / "trash").mkdir(exist_ok=True)
    return d


def load_json(path: Path, default):
    """Load JSON, treating a missing OR corrupted file as `default` rather
    than crashing — state files here are conveniences/caches, never the
    only copy of anything that matters, so degrading to "start fresh" is
    always the safe choice."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def is_noise(name: str) -> bool:
    if name in NOISE_NAMES:
        return True
    return any(name.endswith(suf) for suf in NOISE_SUFFIXES)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_run_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def acquire_lock(state: Path) -> tuple[bool, str]:
    """Try to acquire the single run lock for this state dir. Returns
    (acquired, message). A lock older than LOCK_STALE_SECONDS is treated as
    abandoned (a crashed prior run) and reclaimed automatically — this
    workflow has no supervisor process to clean up after a crash, so a
    lock that can never expire would be worse than the rare double-run it
    guards against."""
    lock_path = state / "run.lock"
    now = time.time()
    if lock_path.exists():
        try:
            held_since = float(lock_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            held_since = 0.0
        age = now - held_since
        if age < LOCK_STALE_SECONDS:
            return False, (
                f"another run appears to be in progress (lock is {age:.0f}s old, "
                f"stale threshold is {LOCK_STALE_SECONDS}s) — stop rather than risk "
                f"double-processing the same files"
            )
    lock_path.write_text(str(now), encoding="utf-8")
    return True, "lock acquired"


def release_lock(state: Path) -> None:
    lock_path = state / "run.lock"
    lock_path.unlink(missing_ok=True)


def append_log_entries(entries: list[dict], state: Path) -> None:
    """Append entries to log.jsonl (append-only audit trail), regenerate
    the trimmed log-summary.md, and update needs-review.json so files
    awaiting a decision stay visible without anyone having to re-read the
    full log."""
    if not entries:
        return
    log_path = state / "log.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        for entry in entries:
            entry.setdefault("logged_at", utc_now_iso())
            f.write(json.dumps(entry, sort_keys=True) + "\n")
    _regenerate_summary(state)
    _update_needs_review(entries, state)


def _regenerate_summary(state: Path) -> None:
    log_path = state / "log.jsonl"
    if not log_path.exists():
        return

    runs: dict[str, dict[str, int]] = {}
    run_order: list[str] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        run_date = entry.get("run_date", "unknown")
        action = entry.get("action", "unknown")
        if run_date not in runs:
            runs[run_date] = {}
            run_order.append(run_date)
        runs[run_date][action] = runs[run_date].get(action, 0) + 1

    recent = run_order[-MAX_SUMMARY_RUNS:]
    lines = ["# Downloads Maintenance — Recent Runs\n"]
    lines.append(
        f"Showing the last {len(recent)} run(s). Full audit trail: `log.jsonl`. "
        f"Files still awaiting a decision: `needs-review.json`.\n"
    )
    for run_date in reversed(recent):
        lines.append(f"## {run_date}")
        for action, count in sorted(runs[run_date].items()):
            lines.append(f"- {action}: {count}")
        lines.append("")

    (state / "log-summary.md").write_text("\n".join(lines), encoding="utf-8")


def _update_needs_review(entries: list[dict], state: Path) -> None:
    """needs-review.json is the small, bounded, always-current answer to
    "which files are still waiting on a decision" — reading it costs far
    less than scanning all of log.jsonl for the most recent action per
    path, which is what step 1 would otherwise require every single run."""
    nr_path = state / "needs-review.json"
    needs_review = load_json(nr_path, {})

    for entry in entries:
        path = entry.get("path")
        action = entry.get("action")
        if not path or not action:
            continue
        if action == "needs_review":
            needs_review.setdefault(path, {
                "category": entry.get("category", "Other/Unclear"),
                "since_run_date": entry.get("run_date"),
            })
        elif action in RESOLVING_ACTIONS:
            needs_review.pop(path, None)

    save_json(nr_path, needs_review)
