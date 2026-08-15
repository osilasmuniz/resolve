---
name: downloads-categorization-archival
description: Weekly maintenance workflow that scans the local Downloads folder, categorizes every file, checks each one against the Ax Legal SharePoint site for an existing copy, deletes local duplicates that are already safely stored in SharePoint, and routes new international-client files into an "Allocate Properly" folder at the SharePoint root — asking Silas where to file anything else. Use this skill whenever asked to clean up, organize, categorize, or archive the Downloads folder; to run "downloads maintenance" or "downloads cleanup"; to free up local disk space while keeping Ax Legal SharePoint as the source of truth; or when setting up, running, or checking the weekly Wednesday Downloads cleanup. Also trigger on phrases like "clean up my downloads", "what's cluttering my downloads folder", "archive downloads to SharePoint", "categorize my downloads", or "set up weekly downloads cleanup".
---

# Downloads Categorization & Archival

A weekly janitor for Silas's local Downloads folder. It keeps Downloads from
turning into a junk drawer, while treating **Ax Legal's SharePoint as the
single source of truth** — nothing meaningful ever exists *only* in Downloads
for long, and nothing gets deleted locally unless a verified copy already
lives in SharePoint.

## Why this is designed the way it is

Downloads folders accumulate two very different kinds of file: things that
were already saved properly somewhere else (an invoice PDF that's already
sitting in the Ax Legal SharePoint, a contract Silas already filed) and
things that were never filed at all. The first kind is safe to delete
locally — SharePoint already has it. The second kind is *not* safe to guess
about, especially when it may belong to a client matter. Guessing wrong on a
legal/tax document is a much worse outcome than leaving a file sitting in
Downloads for one more week.

So the workflow has exactly one irreversible-feeling action (local deletion)
and it is gated behind exactly one condition: **a verified duplicate already
exists in the Ax Legal SharePoint.** Everything else is either a SharePoint
upload (reversible — SharePoint has version history and a recycle bin) or a
question to Silas. Even the "irreversible" local deletion isn't immediate —
see [Staged deletion](#staged-deletion-never-immediate-rm), below.

## Prerequisites

- The `ms365` connector (SharePoint + Outlook) must be connected. If
  SharePoint tools aren't available, stop and tell Silas to connect it
  rather than guessing at file placement.
- A local state directory at `~/.downloads-maintenance/` (created
  automatically on first run — see [State layout](#local-state-layout)).
- Confirm the Downloads path once per machine (default `~/Downloads`); don't
  assume it if the user has a nonstandard setup.

## The sequence

### 0. Acquire the run lock

Run `python scripts/lock.py acquire`. If it exits non-zero, another run
(the weekly trigger and a manual invocation, most likely) is already in
progress — stop here entirely, don't scan or touch anything. Run
`python scripts/lock.py release` at the end of the sequence, including if
you stop early (missing connector, lock already held, etc.) — every exit
path must release a lock it acquired.

### 1. Scan Downloads

Run `python scripts/scan_downloads.py <downloads-path>` (no flags yet —
see below). It recursively lists every file (skipping OS noise like
`.DS_Store`, `desktop.ini`, `Thumbs.db`, in-progress downloads like
`*.crdownload`/`*.part`/`*.tmp`, and symlinks), hashes each one (SHA-256),
and diffs against `~/.downloads-maintenance/manifest-cache.json` from the
last run to report which files are `new`, `changed`, `unchanged_count`, and
`removed_count`.

**Only the `new` and `changed` files need full processing** (steps 2-5) —
that's the whole point of the incremental scan, see
`references/token-and-memory-optimization.md`. Separately, read
`~/.downloads-maintenance/needs-review.json` (small and always current) to
re-surface files left over from prior runs that still need a decision —
they don't need re-scanning to be worth mentioning in this run's report.

**Do not pass `--commit` on this first call.** The manifest cache should
only be updated once this run has actually finished processing every
new/changed file — that way a crash or timeout partway through doesn't
cause an unprocessed file to be wrongly marked "already seen" and silently
skipped forever. Once steps 2-6 are done for every new/changed file, re-run
`python scripts/scan_downloads.py <downloads-path> --commit` (same
arguments, no need to re-process anything — this second call just persists
the cache).

### 2. Categorize each new/changed file

Apply the taxonomy in `references/categorization-policy.md` (file type +
filename/content signals → category: Tax Documents, Client Correspondence,
Invoices & Billing, Contracts & Legal, Screenshots & Temp, Personal,
Other/Unclear). Categorization drives which SharePoint library/folder to
search in step 3 and, for unmatched files, which folder to suggest in step
4. Don't open every file's full contents to categorize it — filename,
extension, size, and a light read of the first page/lines is normally
enough. Only fully read a file's content when the filename is genuinely
uninformative (e.g. `IMG_4821.pdf`, `Untitled document.docx`).

### 3. Check whether Ax Legal SharePoint already has it

The very first run on a machine won't have `sharepoint-cache.json` yet —
`references/sharepoint-duplicate-check.md` opens with exactly how to
resolve the Ax Legal site once and cache it, so start there rather than
guessing at a site name or URL.

Then: search the Ax Legal site for the same or a normalized filename plus
category-appropriate folders, and judge confidence from name + size +
modified date (SharePoint search is keyword-based, not a hash comparison,
so exact certainty isn't always available — use judgment, and when
confidence is only medium, treat it as **not found** rather than guessing
yes; see that reference file for what "medium confidence" looks like and
why guessing yes is the worse mistake).

- **High-confidence match found** → this file is a confirmed duplicate.
  Note the SharePoint URL you matched it against (you'll need it in step 5)
  and go there. Do not ask the user — that would just be friction for
  something SharePoint already has safely.
- **No match / low confidence** → go to step 4.

### 4. Route files with no confirmed SharePoint copy

- If the file relates to one of Ax Legal's **international clients**
  (per `references/international-clients.md`), upload it to the
  `Allocate Properly` folder at the root of the Ax Legal SharePoint site
  (create that folder once, if it doesn't already exist, then cache its
  folder ID/URL — see `sharepoint-duplicate-check.md`). After a verified
  successful upload, note the resulting SharePoint URL and go to step 5 —
  "uploaded" and "verified present at destination" are different facts,
  don't collapse them; the upload confirmation *is* the evidence step 5
  needs.
- If the client/matter is unclear or the file isn't tied to a known
  international client, **do not guess**. In an interactive session, ask
  the user directly (`AskUserQuestion` is a good fit — offer the most
  likely SharePoint destination folders as options, plus "leave in
  Downloads for now"). In an unattended weekly run (see
  [Scheduling](#weekly-scheduling)) there's no one to ask synchronously —
  leave the file untouched in Downloads and log it with action
  `needs_review` (step 6); it'll show up in `needs-review.json` for Silas
  automatically from then on, no re-scanning required.
- The very first time a client name shows up that isn't yet in
  `international-clients.json`, ask Silas once whether that client is
  international (and should therefore route to Allocate Properly) or
  domestic, then persist the answer to
  `~/.downloads-maintenance/international-clients.json` so future runs
  don't ask again. Never infer a client's international status from a
  name alone.

### 5. Staged deletion — never immediate `rm`

For every file confirmed as a SharePoint duplicate (step 3) or
successfully uploaded (step 4), run:

```
python scripts/stage_for_deletion.py <downloads-path> <relative-file-path> \
    --action staged_duplicate \
    --category "<category from step 2>" \
    --sharepoint-url "<the URL you verified/uploaded to>"
```

(`--action` is `staged_duplicate` for a confirmed SharePoint duplicate from
step 3, or `uploaded_allocate_properly` for a file just uploaded in step 4
— the two paths that lead here.)

This is the **only** way a file should ever leave Downloads in this skill
— never move or delete a Downloads file with a raw shell command. The
script moves (not copies-then-deletes) the file into
`~/.downloads-maintenance/trash/<run-date>/`, preserving its relative
path, refuses to silently overwrite a same-day collision, and writes a
`.meta.json` sidecar recording the SharePoint evidence — plus it logs the
action itself, so you don't need a separate `append_log.py` call for this
one. This is the same "stage instead of destroy" philosophy used elsewhere
for Silas's file cleanup: it gives a grace window to notice a bad match
before the bytes are actually gone.

A file sitting in `trash/` for longer than the grace period is eligible
for permanent deletion by `scripts/purge_trash.py`, which the weekly run
calls at the very end (after step 6). The grace period's policy value
lives in `references/categorization-policy.md` (default 14 days) — that
document is the actual source of truth, so pass it explicitly:
`python scripts/purge_trash.py --grace-days <value from the policy doc>`.
The script's own default only matches the policy doc as a fallback; if
Silas asks to change the grace period, update the policy doc *and* make
sure future runs pass the new value. Every permanent deletion is logged
with the original path, the SharePoint URL it was verified against
(pulled from the `.meta.json` sidecar), and the date it was first staged.

### 6. Log everything else

For every other action this run took — `scanned`, `categorized`,
`matched_duplicate`, `needs_review` — collect the entries as you go and
call `scripts/append_log.py` **once at the end of the run** with the full
list (via `--entries a-file.json` or piping a JSON array to stdin), rather
than once per file. `staged_duplicate` and `uploaded_allocate_properly`
are already logged by `stage_for_deletion.py` in step 5 — don't log those
twice. These seven action names
(`scanned`/`categorized`/`matched_duplicate`/`staged_duplicate`/`uploaded_allocate_properly`/`needs_review`/`purged`)
are the only ones any part of this skill should ever write — using a
different spelling anywhere fragments `log-summary.md`'s per-action
counts.

`append_log.py` also regenerates `log-summary.md` (last 8 runs only) and
`needs-review.json` automatically — you never need to hand-edit either.
See `references/token-and-memory-optimization.md` for why both stay small
by design. `log.jsonl` itself is the durable, complete audit trail; never
delete it, only append.

### 7. Report back, then release the lock

End every run — attended or unattended — with a short summary: files
scanned, categorized breakdown, duplicates staged for deletion, files
uploaded to Allocate Properly, and the current `needs-review.json` list.
Don't paste the full JSONL log into the conversation; that defeats the
point of keeping it on disk. Finally, run
`python scripts/lock.py release` — every run that acquired the lock in
step 0 must release it here, or on any early-exit path, so the next run
(scheduled or manual) isn't blocked by a lock nothing is still holding.

## Weekly scheduling

This skill is meant to run unattended every **Wednesday**. Set it up with
`create_trigger` (see `references/scheduling.md` for the exact cron
expression, the UTC-conversion worked example, and why it binds to the
existing session rather than spawning a fresh one each time). Confirm the
desired local time with Silas before creating the trigger — don't assume a
time.

## Guardrails (don't skip these)

- Never move or delete a Downloads file except through
  `scripts/stage_for_deletion.py` — it's the one place that enforces
  "no move without SharePoint evidence."
- Never delete a file that hasn't been matched against SharePoint with high
  confidence in this run.
- Never upload a file to "Allocate Properly" — or anywhere in SharePoint —
  for a client that hasn't been explicitly confirmed as international.
- Never invent or guess a client's international status; ask once, then
  remember the answer. If `international-clients.json` is missing or
  fails to parse, treat it as empty and re-ask rather than guessing from
  whatever partial data might be recoverable.
- If the `ms365` SharePoint connector isn't available, stop and say so
  instead of silently skipping the duplicate-check step (silently skipping
  it would make every file look like "no match found," which is safe but
  misleading — surface the real reason).
- Always acquire the run lock (step 0) before touching anything, and
  always release it (step 7) before ending the run — including on every
  early-exit path (missing connector, lock already held by another run).
- Treat `log.jsonl` as append-only. It's the audit trail for every file
  this skill has ever touched.

## Reference files

- `references/categorization-policy.md` — the category taxonomy and the
  grace-period policy value.
- `references/sharepoint-duplicate-check.md` — first-run site resolution,
  how to search SharePoint, and how to judge match confidence.
- `references/international-clients.md` — how the international-client
  list works and how it's learned over time.
- `references/scheduling.md` — the weekly Wednesday trigger setup.
- `references/token-and-memory-optimization.md` — why re-scans are
  incremental, why the log is rolling, and a NotebookLM-assisted
  suggestion for further cutting token spend on large document sets.

## Local state layout

```
~/.downloads-maintenance/
├── manifest-cache.json          # hash/size/mtime of every file seen, for incremental scans
├── needs-review.json            # small, always-current list of files still awaiting a decision
├── international-clients.json   # learned client -> international? mapping (see references/international-clients.md)
├── sharepoint-cache.json        # cached Ax Legal site id + Allocate Properly folder id/URL
├── log.jsonl                    # append-only audit trail, one JSON object per line
├── log-summary.md               # rolling human-readable summary, last 8 runs only
├── run.lock                     # held for the duration of one run; auto-reclaimed if stale
└── trash/
    └── <run-date>/
        ├── <relative/path/to/file>            # staged file, preserving Downloads-relative path
        └── <relative/path/to/file>.meta.json  # SharePoint evidence, read by purge_trash.py
```
