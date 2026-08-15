# Categorization Policy

## Category taxonomy

Assign every file exactly one primary category. When a file could plausibly
fit two, prefer the more specific one (a signed contract PDF from a client
is "Contracts & Legal", not "Client Correspondence", even though it arrived
by email).

| Category | Typical signals |
|---|---|
| **Tax Documents** | DARF PDFs, Carnê-Leão spreadsheets, IRRF calculations, SICALC receipts, `.xlsx`/`.pdf` with tax keywords (imposto, DARF, IRRF, carnê-leão, receita) |
| **Invoices & Billing** | Harvest invoice exports, PTAX/exchange-rate sheets, filenames with "invoice", "fatura", "NF-e" |
| **Client Correspondence** | Emails saved as `.msg`/`.eml`, exported chat threads, letters addressed to/from a named client |
| **Contracts & Legal** | Signed agreements, NDAs, powers of attorney, anything with "contrato", "agreement", "procuração" |
| **Screenshots & Temp** | `Screenshot*`, `image*.png`, files under a few KB with generic camera/screenshot naming, obvious scratch files |
| **Personal** | Content clearly unrelated to Ax Legal work (confirm with filename/context, don't open personal files further than necessary to classify them) |
| **Other/Unclear** | Anything that doesn't fit cleanly — these are exactly the files that need the `needs-review` path in SKILL.md step 4, never a guessed category |

Category determines which SharePoint library/folder to search first in
`sharepoint-duplicate-check.md`, and which folder to propose to Silas when a
file has no confirmed home.

## Reading file content

Filename + extension + size are usually enough to categorize. Only open a
file's actual content when the filename is uninformative (`IMG_4821.pdf`,
`Untitled document.docx`, `download (3).xlsx`). Even then, a first page or
first few hundred characters is normally sufficient — categorization needs
a signal, not a full read. This matters for token spend on months where
Downloads has accumulated a lot of low-signal files; see
`token-and-memory-optimization.md`.

## Config knobs

- **Trash grace period: 14 days.** This document is the source of truth
  for the value — `scripts/purge_trash.py --grace-days 14` is only a
  fallback default that happens to match it. If Silas asks to change the
  grace period, update the number here *and* make sure the next run
  actually passes `--grace-days <new value>` (SKILL.md step 5 says to read
  the value from here explicitly, precisely so this file isn't just prose
  that nothing enforces). This is the one safety margin standing between
  "matched with high confidence" and "gone" — don't shorten it without
  Silas's agreement.
- **Files awaiting a decision stay visible without a re-scan.** A file
  logged with action `needs_review` is tracked in
  `~/.downloads-maintenance/needs-review.json` until a later run resolves
  it (matches a SharePoint duplicate, gets uploaded, or gets purged) — see
  SKILL.md step 6. That file is small and cheap to read every run, so
  there's no need to re-search SharePoint for these files on any
  particular cadence; only re-search one if something about the file
  itself changes (which `scan_downloads.py` will surface as `changed`) or
  Silas specifically asks.
