# Telegram Intake & Public-Profile Check Bot

A small bot that runs on your laptop and writes to one Excel file, **Telegram Bot Log.xlsx**:

| Sheet | What fills it | Data recorded |
|---|---|---|
| **Contacts** | Anyone who messages the bot | Telegram user ID, @username, first/last name, language, first/last contact, message count |
| **Checks** | You send `/check @username` | Public name/title, bio/description, type (user/bot/channel/group), member count (channels/groups), Telegram ID (channels/groups only), source |

**Data sources:** Telegram only (the official Bot API and the public `t.me/username` page).
No phone numbers, no third-party lookup sites, no leaked databases.

---

## One-time setup (about 15 minutes)

### Step 1: Install Python
- **Windows:** go to <https://www.python.org/downloads/> and click *Download Python*.
  When the installer opens, **tick "Add python.exe to PATH"**, then click *Install Now*.
- **Mac:** same link, download and run the installer.

### Step 2: Create your bot in Telegram
1. In Telegram, search for **@BotFather** (blue verified tick) and press *Start*.
2. Send `/newbot`.
3. Give it a display name (e.g. *Ax Legal Intake*), then a username ending in `bot` (e.g. `axlegal_intake_bot`).
4. BotFather replies with a **token** like `123456789:AAH...`. Keep it private, since anyone with it controls the bot.

### Step 3: Put the files on your laptop
1. Download this `telegram-bot` folder (e.g. to `Documents\telegram-bot`).
2. Make a copy of `config.example.ini` and rename the copy to `config.ini`.
3. Open `config.ini` in Notepad (Windows) or TextEdit (Mac) and replace `PASTE_YOUR_BOT_TOKEN_HERE` with your token. Save.

### Step 4: Install the two libraries
Open a terminal in the folder:
- **Windows:** open the folder in File Explorer, click the address bar, type `cmd`, press Enter.
- **Mac:** right-click the folder → *New Terminal at Folder*.

Then run:
```
pip install -r requirements.txt
```
(Mac: use `pip3` if `pip` is not found.)

### Step 5: Start the bot and set yourself as owner
```
python telegram_bot.py
```
(Mac: `python3 telegram_bot.py`.) You should see `Bot @yourbot is running`.

1. In Telegram, open your bot, press *Start*, and send `/myid`.
2. Copy the number into `config.ini` after `owner_id =`. Save.
3. In the terminal press **Ctrl+C** to stop, then start it again.

Setup is now complete. Only your account can run `/check`.

---

## Daily use

| You send the bot | Result |
|---|---|
| `/check @username` | Public details recorded in **Checks** and replied in chat |
| `/check https://t.me/username` | Same |
| `/myid` | Your Telegram ID |
| `/help` | Command list |

- **The bot only works while the terminal window is open and the laptop is awake.** Messages sent while it is off are delivered when you restart it (Telegram holds them for 24 hours).
- You can open the Excel file at any time. If it is open while a new row arrives, the bot keeps the row in memory and saves it once you close the file.
- To stop the bot, press **Ctrl+C** in the terminal.

---

## Limits (what the bot cannot do)

- **Users can only be looked up by @username, not by numeric ID.** Telegram does not reveal a person's profile from a numeric ID unless that person has messaged your bot. If they have, their details are already in **Contacts**.
- **Users without a public @username cannot be checked.**
- **A person's numeric Telegram ID is not shown on the public page.** It is only captured when they message the bot.
- **Hidden profile details stay hidden.** A user's privacy settings decide whether the bio is visible.
- **"Type = Bot" is inferred from the username.** Telegram requires every bot's username to end in "bot", so the tool assumes that ending means a bot. A person could use that ending too, so confirm on the profile if it matters.
- **The data is a snapshot taken when the check ran.** Names, usernames and bios can change at any time. Re-check before relying on them.

## Compliance notes (for review before client use)

- **Contacts sheet.** This is personal information under **PIPEDA** in Canada (S.C. 2000, c. 5, Schedule 1, Principles 4.2 *Identifying Purposes* and 4.3 *Consent*) and **BC PIPA** (S.B.C. 2003, c. 63, ss. 6–10). In Brazil, the **LGPD** (Lei 13.709/2018, arts. 7 and 9) applies. The `/start` message tells users what is recorded, and you can customize it via `privacy_notice` in `config.ini`. Confirm the wording and the retention period before client use.
- **Checks sheet.** It holds only publicly displayed data, but **public is not consent-free** under the statutes above. Record the matter or purpose for each check, keep a human review step, and do not use the results as identity verification on their own.
- **Keep the Excel file confidential.** Store it in the same location as other client files, not in a personal or shared folder.
