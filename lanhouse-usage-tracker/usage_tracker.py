#!/usr/bin/env python3
"""
usage_tracker.py  --  LAN-house application-usage logger for billing.

WHAT IT DOES
    From the moment a session starts (after the customer accepts the on-screen
    billing notice) until the machine is shut down or the user logs out, it
    records which application is in the foreground and for how long, writes a
    plain-text session log, and emails that log for billing.

WHAT IT DOES NOT DO
    It does not hide from the user, capture keystrokes, read window contents,
    open files, or take screenshots. It records only the application name and
    elapsed seconds -- the minimum needed to bill time. The notice in
    consent.py tells the customer exactly this, every session.

    It reads the frontmost app via NSWorkspace, which does NOT require
    Accessibility permission (that permission is only needed to read window
    titles or keystrokes -- which we deliberately do not do).

HOW IT STOPS
    launchd sends SIGTERM at logout/shutdown. We catch it, write the final
    log, and email the report before exiting.
"""
import atexit
import signal
import smtplib
import ssl
import sys
import time
from collections import defaultdict
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

import config

try:
    from AppKit import NSWorkspace  # provided by pyobjc (see README)
except ImportError:
    NSWorkspace = None


# --- usage accumulation ------------------------------------------------------
usage_seconds: dict[str, float] = defaultdict(float)
session_start = datetime.now()
_finalized = False


def frontmost_app_name() -> str:
    if NSWorkspace is None:
        return "Unknown"
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return "Unknown"
    return app.localizedName() or "Unknown"


def log_path() -> Path:
    day = session_start.strftime("%Y%m%d")
    Path(config.LOG_DIR).mkdir(parents=True, exist_ok=True)
    return Path(config.LOG_DIR) / f"{day} {config.STATION_NAME} usage.txt"


def build_report() -> str:
    end = datetime.now()
    lines = [
        "LAN-House Application Usage Report",
        "=" * 40,
        f"Station : {config.STATION_NAME}",
        f"Session : {session_start:%Y-%m-%d %H:%M:%S}  ->  {end:%Y-%m-%d %H:%M:%S}",
        f"Total   : {format_hms(sum(usage_seconds.values()))}",
        "",
        f"{'Application':<32}{'Time (h:m:s)':>14}",
        "-" * 46,
    ]
    for name, secs in sorted(usage_seconds.items(), key=lambda kv: -kv[1]):
        if secs >= config.MIN_SECONDS_TO_REPORT:
            lines.append(f"{name[:32]:<32}{format_hms(secs):>14}")
    lines.append("")
    return "\n".join(lines)


def format_hms(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def write_log(report: str) -> None:
    path = log_path()
    path.write_text(report, encoding="utf-8")
    # Owner (admin) read/write only -- a normal customer account cannot edit it.
    try:
        path.chmod(0o600)
    except PermissionError:
        pass


def email_report(report: str) -> None:
    if not config.SMTP_PASSWORD:
        # No password configured yet -- log is still written locally.
        return
    msg = EmailMessage()
    msg["Subject"] = (
        f"Usage report - {config.STATION_NAME} - "
        f"{session_start:%Y-%m-%d}"
    )
    msg["From"] = config.REPORT_FROM
    msg["To"] = config.REPORT_TO
    msg.set_content(report)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as smtp:
        smtp.starttls(context=ctx)
        smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        smtp.send_message(msg)


def finalize(*_args) -> None:
    global _finalized
    if _finalized:
        return
    _finalized = True
    report = build_report()
    write_log(report)
    try:
        email_report(report)
    except Exception:
        # Never crash on shutdown; the local log is the source of truth.
        pass
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, finalize)
    signal.signal(signal.SIGINT, finalize)
    atexit.register(finalize)

    last = time.monotonic()
    while True:
        time.sleep(config.POLL_SECONDS)
        now = time.monotonic()
        usage_seconds[frontmost_app_name()] += now - last
        last = now
        # Periodic flush so a hard power-off still leaves a recent log.
        write_log(build_report())


if __name__ == "__main__":
    main()
