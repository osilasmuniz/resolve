# =============================================================================
# CONFIGURATION  --  edit these values before deploying on each Mac
# =============================================================================
# Nothing here is a secret you type into the code except the SMTP app-password,
# and even that should be moved to the macOS Keychain in production (see README).
# For a first run you may put it here; the README shows the Keychain method.

# --- Where the daily/session report is emailed -------------------------------
REPORT_TO      = "billing@example.com"      # who receives the usage reports
REPORT_FROM    = "lanhouse.tracker@example.com"  # sending account
SMTP_HOST      = "smtp.gmail.com"           # e.g. Gmail: smtp.gmail.com
SMTP_PORT      = 587                          # 587 = STARTTLS
SMTP_USERNAME  = "lanhouse.tracker@example.com"
SMTP_PASSWORD  = ""   # app-specific password. Leave "" and use Keychain (README).

# --- Machine identity (shows up in the report and file name) -----------------
STATION_NAME   = "Station-01"               # rename per computer

# --- Logging behaviour -------------------------------------------------------
POLL_SECONDS   = 5      # how often to check which app is in front
LOG_DIR        = "/Library/Application Support/LanHouseTracker"  # admin-owned
MIN_SECONDS_TO_REPORT = 5   # ignore apps used less than this (noise)

# --- Consent notice shown to the customer at the start of every session ------
# This on-screen notice is what makes the logging lawful. Do NOT remove it.
CONSENT_TITLE  = "Computer Usage Notice"
CONSENT_TEXT   = (
    "This computer records which applications are used and for how long, "
    "for billing purposes only. No keystrokes, passwords, screen contents, "
    "or personal files are recorded.\n\n"
    "By clicking “I Agree” and using this computer, you consent to "
    "this billing log."
)
CONSENT_AGREE  = "I Agree"
CONSENT_DECLINE = "Do Not Use"
