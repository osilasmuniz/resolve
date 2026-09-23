# LAN-House Usage Tracker (macOS)

A small, **transparent** application-usage logger for billing computers you own
(e.g. a LAN house / internet café). It records **which app was in front and for
how long**, per customer session, writes a plain-text log, and emails it for
billing. It shows a consent notice at the start of every session.

## What it records — and what it deliberately does not

| Records | Does **not** record |
|---|---|
| Application name (e.g. "Google Chrome") | Keystrokes / passwords |
| Seconds spent in each app | Window titles or screen contents |
| Session start/end, station name, date | Files, documents, browsing history |

It reads the foreground app through macOS `NSWorkspace`, which needs **no
Accessibility permission** — because we never read keystrokes or window
contents. That limitation is a feature: it keeps the tool lawful and simple.

## Why it is not hidden

The tool runs as a normal background service (no window while tracking — that is
just how a service behaves), but it is **not concealed from the user**, and it
must not be. Two things make the billing log legally usable and
tamper-defensible:

1. **A consent notice every session** (`consent.py`). Because different
   customers share the same machine, each is a separate person who must be told.
   A one-time notice would not cover later customers. So the notice appears
   **at every login/boot**, and the customer clicks *I Agree* to proceed.
2. **File permissions, not secrecy.** The log lives under an admin-owned folder
   (`/Library/Application Support/LanHouseTracker`) with `0600` permissions and
   is owned by the operator account. An ordinary customer account cannot edit
   it. That is how you prevent adulteration — with OS permissions, not by hiding
   that logging happens.

> Covertly monitoring individuals (hidden process, no notice, silent
> exfiltration) is the stalkerware pattern and is unlawful in both Brazil (LGPD)
> and Canada/BC (PIPA). This tool intentionally does the disclosed equivalent,
> which bills just as accurately.

## Files

| File | Purpose |
|---|---|
| `config.py` | All settings you edit (email, station name, consent text). |
| `consent.py` | The per-session billing notice dialog. |
| `usage_tracker.py` | The tracker: logs usage, writes file, emails report. |
| `start_session.sh` | Runs consent, then the tracker, at each login. |
| `com.axlegal.usagetracker.plist` | LaunchAgent that starts it at login. |

---

## What to configure on each Mac before it goes live

### 1. Create a dedicated operator (admin) account
Log-keeping and the LaunchAgent belong to an **operator/admin** account,
separate from the **customer** account customers actually use. Customers use a
standard (non-admin) account so they cannot reach the operator's files.

### 2. Install Python + the one dependency
macOS ships `python3`. Install `pyobjc` (for reading the foreground app):

```bash
# Recommended: a dedicated venv owned by the operator account
python3 -m venv /Library/Application\ Support/LanHouseTracker/venv
sudo /Library/Application\ Support/LanHouseTracker/venv/bin/pip install pyobjc-framework-Cocoa
```

Then set `PYTHON=` in `start_session.sh` to that venv's `python`.

### 3. Copy the project into place
```bash
sudo mkdir -p "/Library/Application Support/LanHouseTracker/app"
sudo cp config.py consent.py usage_tracker.py start_session.sh \
        "/Library/Application Support/LanHouseTracker/app/"
sudo chmod 755 "/Library/Application Support/LanHouseTracker/app/start_session.sh"
sudo chown -R root:wheel "/Library/Application Support/LanHouseTracker"
```

### 4. Fill in `config.py`
- `REPORT_TO`, `REPORT_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`
- `STATION_NAME` (unique per computer)
- Review `CONSENT_TEXT` — put it in the customer's language.

### 5. Set up the sending email (app password)
For Gmail/Outlook you need an **app-specific password** (normal passwords are
rejected for SMTP). Rather than leaving it in `config.py`, store it in the
operator's Keychain and read it at runtime:

```bash
# Store once (operator account):
security add-generic-password -a "lanhouse" -s "usagetracker-smtp" -w "APP_PASSWORD_HERE"
```

Then in `config.py` leave `SMTP_PASSWORD = ""` and add near the top:

```python
import subprocess
SMTP_PASSWORD = subprocess.run(
    ["security", "find-generic-password", "-a", "lanhouse",
     "-s", "usagetracker-smtp", "-w"],
    capture_output=True, text=True).stdout.strip()
```

(For a first test you may temporarily put the app password directly in
`config.py`, then move it to Keychain before going live.)

### 6. Allow outbound SMTP on the network
Make sure the LAN house firewall/router permits outbound port **587** to your
mail provider, or reports won't send (the local log is still written either way).

### 7. Install the LaunchAgent
```bash
sudo cp com.axlegal.usagetracker.plist /Library/LaunchAgents/
sudo chown root:wheel /Library/LaunchAgents/com.axlegal.usagetracker.plist
sudo chmod 644 /Library/LaunchAgents/com.axlegal.usagetracker.plist
# Load for the current login session (or just reboot):
launchctl bootstrap gui/$(id -u) /Library/LaunchAgents/com.axlegal.usagetracker.plist
```

### 8. Post the notice (compliance)
Put a short printed sign at each station: *"These computers log application
usage for billing. By using them you agree."* The on-screen dialog plus the
sign together satisfy the transparency requirement.

---

## Testing it

```bash
# Run once by hand as the operator account:
/path/to/python usage_tracker.py    # Ctrl-C to stop -> writes + emails report
```

Check the log at
`/Library/Application Support/LanHouseTracker/YYYYMMDD Station-01 usage.txt`
and confirm the email arrives.

## Before/after note (for the AI-adoption portfolio)
- **Before:** attendant estimates time by watching the clock / paper log.
- **After:** per-app time captured automatically, emailed per session, log
  tamper-resistant by file permissions, consent recorded each session.
- **Governance:** disclosed collection, minimal data (app + duration only), no
  keystroke/screen capture, retention/erasure policy set by the operator.
