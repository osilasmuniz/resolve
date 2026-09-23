#!/usr/bin/env python3
"""
consent.py  --  Show the billing-notice dialog at the start of a session.

Runs at login/boot BEFORE tracking begins. If the customer clicks the decline
button, we exit non-zero and the tracker is not started for that session.

Uses osascript (built into macOS) so there is no extra dependency and the
dialog looks native. This dialog is intentionally visible -- it is the consent
step that makes the usage logging lawful and the log tamper-defensible.
"""
import subprocess
import sys

import config


def ask_consent() -> bool:
    script = (
        f'display dialog {applescript_quote(config.CONSENT_TEXT)} '
        f'with title {applescript_quote(config.CONSENT_TITLE)} '
        f'buttons {{{applescript_quote(config.CONSENT_DECLINE)}, '
        f'{applescript_quote(config.CONSENT_AGREE)}}} '
        f'default button {applescript_quote(config.CONSENT_AGREE)} '
        f'with icon note'
    )
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
    )
    # osascript prints "button returned:I Agree" on OK, exits non-zero on Cancel.
    return config.CONSENT_AGREE in (result.stdout or "")


def applescript_quote(text: str) -> str:
    """Return an AppleScript string literal (double-quoted, escaped)."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


if __name__ == "__main__":
    sys.exit(0 if ask_consent() else 1)
