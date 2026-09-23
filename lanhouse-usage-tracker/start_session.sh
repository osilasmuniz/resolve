#!/bin/bash
# start_session.sh -- launched at each login/boot by the LaunchAgent.
# 1) Shows the billing-notice dialog (consent.py).
# 2) Only if the customer agrees, starts the usage tracker for the session.
#
# Edit PYTHON to the interpreter that has pyobjc installed (see README).

HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="/usr/bin/python3"     # or the venv python from the README

# Ask consent. If declined (non-zero), do not track this session.
if "$PYTHON" "$HERE/consent.py"; then
    exec "$PYTHON" "$HERE/usage_tracker.py"
else
    exit 0
fi
