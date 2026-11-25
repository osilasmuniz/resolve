"""
Telegram Intake & Public-Profile Check Bot
==========================================

What it does
------------
1. Contact log: when anyone messages the bot, it records the data Telegram
   itself provides about that sender (user ID, @username, first/last name,
   language, first/last contact, message count) in the "Contacts" sheet.
2. Public check: the owner sends  /check @username  (or a t.me link) and the
   bot records the PUBLIC profile details of that user, bot, channel or group
   in the "Checks" sheet.

Data sources are first-party Telegram only:
  - Telegram Bot API (getChat)            -> public channels and groups
  - Telegram's public preview page t.me/x -> public name/bio of users and bots
No third-party lookup services, phone numbers or leaked data are used.

Run:  python telegram_bot.py      (stop with Ctrl+C)
"""

import configparser
import html
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.ini"

CONTACT_HEADERS = [
    "Telegram User ID", "Username", "First Name", "Last Name", "Language",
    "Is Bot", "First Contact (UTC)", "Last Contact (UTC)", "Message Count",
]
CHECK_HEADERS = [
    "Checked At (UTC)", "Query", "Result", "Type", "Name / Title",
    "Username", "Bio / Description", "Members / Subscribers", "Telegram ID",
    "Source",
]
COLUMN_WIDTHS = {"Bio / Description": 60, "Query": 28, "Name / Title": 30}


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
def load_config():
    if not CONFIG_FILE.exists():
        sys.exit("config.ini not found. Copy config.example.ini to config.ini "
                 "and fill in your bot token (see README.md).")
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FILE, encoding="utf-8")
    s = cfg["bot"]
    token = s.get("token", "").strip()
    if not token or token.startswith("PASTE"):
        sys.exit("Please paste your bot token into config.ini (see README.md).")
    owner = s.get("owner_id", "").strip()
    return {
        "token": token,
        "owner_id": int(owner) if owner.isdigit() else None,
        "excel_file": BASE_DIR / s.get("excel_file", "Telegram Bot Log.xlsx"),
        "privacy_notice": s.get("privacy_notice", "").strip(),
    }


# --------------------------------------------------------------------------
# Excel storage
# --------------------------------------------------------------------------
class ExcelLog:
    """Writes to an .xlsx file. If the file is open in Excel (locked), rows
    are kept in memory and saved automatically on the next successful write."""

    def __init__(self, path):
        self.path = path
        self.dirty = False
        if path.exists():
            self.wb = load_workbook(path)
        else:
            self.wb = Workbook()
            self.wb.remove(self.wb.active)
        for name, headers in (("Contacts", CONTACT_HEADERS), ("Checks", CHECK_HEADERS)):
            if name not in self.wb.sheetnames:
                self._create_sheet(name, headers)
        self.save()

    def _create_sheet(self, name, headers):
        ws = self.wb.create_sheet(name)
        ws.append(headers)
        for col, title in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F3864")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            letter = cell.column_letter
            ws.column_dimensions[letter].width = COLUMN_WIDTHS.get(title, 20)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    @staticmethod
    def _align_row(ws, row_idx):
        for cell in ws[row_idx]:
            wrap = ws.cell(row=1, column=cell.column).value == "Bio / Description"
            cell.alignment = Alignment(vertical="center", wrap_text=wrap)

    def upsert_contact(self, user, now):
        ws = self.wb["Contacts"]
        for row in ws.iter_rows(min_row=2):
            if row[0].value == user["id"]:
                # Refresh details in case the user changed name/username
                row[1].value = user.get("username", "")
                row[2].value = user.get("first_name", "")
                row[3].value = user.get("last_name", "")
                row[4].value = user.get("language_code", "")
                row[7].value = now
                row[8].value = (row[8].value or 0) + 1
                break
        else:
            ws.append([
                user["id"], user.get("username", ""), user.get("first_name", ""),
                user.get("last_name", ""), user.get("language_code", ""),
                "Yes" if user.get("is_bot") else "No", now, now, 1,
            ])
            self._align_row(ws, ws.max_row)
        ws.auto_filter.ref = ws.dimensions
        return self.save()

    def add_check(self, values):
        ws = self.wb["Checks"]
        ws.append(values)
        self._align_row(ws, ws.max_row)
        ws.auto_filter.ref = ws.dimensions
        return self.save()

    def save(self):
        self.dirty = True
        try:
            self.wb.save(self.path)
            self.dirty = False
            return True
        except PermissionError:
            print(f"[warn] {self.path.name} is open in Excel - will save when it is closed.")
            return False


# --------------------------------------------------------------------------
# Telegram API helpers
# --------------------------------------------------------------------------
class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.session = requests.Session()

    def call(self, method, **params):
        r = self.session.post(self.base + method, data=params, timeout=40)
        return r.json()

    def send(self, chat_id, text):
        self.call("sendMessage", chat_id=chat_id, text=text,
                  disable_web_page_preview="true")


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


USERNAME_RE = re.compile(r"^(?:@|(?:https?://)?(?:t\.me|telegram\.me)/)?([A-Za-z0-9_]{4,32})/?$")


def parse_username(text):
    m = USERNAME_RE.match(text.strip())
    return m.group(1) if m else None


def meta(page, prop):
    m = re.search(rf'<meta property="{prop}" content="([^"]*)"', page)
    return html.unescape(m.group(1)).strip() if m else ""


def div_text(page, css_class):
    m = re.search(rf'<div class="{css_class}"[^>]*>(.*?)</div>', page, re.S)
    if not m:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", m.group(1))
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def check_public(tg, username):
    """Return a dict of public details for @username using first-party sources."""
    result = {"Result": "Not found", "Type": "", "Name / Title": "", "Username": "@" + username,
              "Bio / Description": "", "Members / Subscribers": "", "Telegram ID": "", "Source": ""}

    # 1) Bot API: works for public channels and public groups
    data = tg.call("getChat", chat_id="@" + username)
    if data.get("ok"):
        chat = data["result"]
        count = tg.call("getChatMemberCount", chat_id="@" + username)
        result.update({
            "Result": "Found",
            "Type": chat.get("type", "").replace("supergroup", "group").title(),
            "Name / Title": chat.get("title") or " ".join(
                filter(None, [chat.get("first_name"), chat.get("last_name")])),
            "Bio / Description": chat.get("description") or chat.get("bio") or "",
            "Members / Subscribers": count.get("result", "") if count.get("ok") else "",
            "Telegram ID": chat.get("id", ""),
            "Source": "Telegram Bot API",
        })
        return result

    # 2) Public t.me preview page: works for users and bots with a public username
    try:
        page = requests.get(f"https://t.me/{username}", timeout=20,
                            headers={"User-Agent": "Mozilla/5.0 (TelegramProfileCheck)"}).text
    except requests.RequestException as exc:
        result["Result"] = f"Error: {exc.__class__.__name__}"
        return result

    title = div_text(page, "tgme_page_title")
    if not title:  # t.me shows no title when the username does not exist
        return result
    extra = div_text(page, "tgme_page_extra")
    is_bot = username.lower().endswith("bot")
    members = extra if re.search(r"(member|subscriber)", extra, re.I) else ""
    result.update({
        "Result": "Found",
        "Type": "Bot" if is_bot else ("Channel/Group" if members else "User"),
        "Name / Title": title,
        "Bio / Description": div_text(page, "tgme_page_description") or meta(page, "og:description"),
        "Members / Subscribers": members,
        "Source": "Public t.me page",
    })
    return result


# --------------------------------------------------------------------------
# Bot logic
# --------------------------------------------------------------------------
HELP = (
    "Commands\n"
    "/myid - show your Telegram user ID\n"
    "/check @username - record public profile details (owner only)\n"
    "/help - this message"
)


def handle_message(tg, log, cfg, msg):
    user = msg.get("from")
    if not user or msg.get("chat", {}).get("type") != "private":
        return  # only handle one-to-one chats
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    log.upsert_contact(user, utc_now())

    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()

    if cmd == "/start":
        notice = cfg["privacy_notice"] or (
            "Welcome. Please note this bot records your Telegram user ID, username, "
            "name and language setting to keep a record of who contacted us.")
        tg.send(chat_id, notice)
    elif cmd == "/myid":
        tg.send(chat_id, f"Your Telegram user ID is: {user['id']}")
    elif cmd == "/help":
        tg.send(chat_id, HELP)
    elif cmd == "/check":
        if cfg["owner_id"] is None:
            tg.send(chat_id, "Owner not set. Send /myid, put the number in config.ini "
                             "as owner_id, then restart the bot.")
            return
        if user["id"] != cfg["owner_id"]:
            tg.send(chat_id, "Sorry, this command is restricted.")
            return
        username = parse_username(arg)
        if not username:
            tg.send(chat_id, "Usage: /check @username   or   /check https://t.me/username")
            return
        tg.send(chat_id, f"Checking @{username} ...")
        r = check_public(tg, username)
        saved = log.add_check([utc_now(), arg.strip()] + [r[h] for h in CHECK_HEADERS[2:]])
        lines = [f"{k}: {v}" for k, v in r.items() if v != ""]
        if not saved:
            lines.append("\n(Excel file is open - will save when you close it.)")
        tg.send(chat_id, "\n".join(lines))


def main():
    cfg = load_config()
    tg = Telegram(cfg["token"])
    me = tg.call("getMe")
    if not me.get("ok"):
        sys.exit(f"Telegram rejected the token: {me.get('description')}")
    log = ExcelLog(cfg["excel_file"])
    print(f"Bot @{me['result']['username']} is running. Log file: {cfg['excel_file']}")
    print("Press Ctrl+C to stop.")

    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            updates = tg.call("getUpdates", **params)
            for upd in updates.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    try:
                        handle_message(tg, log, cfg, upd["message"])
                    except Exception as exc:  # keep running on any single bad message
                        print(f"[error] {exc!r}")
            if log.dirty:
                log.save()
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except requests.RequestException as exc:
            print(f"[network] {exc.__class__.__name__} - retrying in 5 s")
            time.sleep(5)


if __name__ == "__main__":
    main()
