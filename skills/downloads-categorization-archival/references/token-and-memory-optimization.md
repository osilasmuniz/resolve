# Token & Memory Optimization

This skill runs weekly, indefinitely. Left unchecked, two things grow
without bound: the number of files re-examined each run, and the size of
the context Claude has to re-read to pick up where the last run left off.
Both are addressed structurally, not by trying to be terse in the moment.

## What's already built in

1. **Incremental scanning.** `scripts/scan_downloads.py` hashes every file
   and diffs against `manifest-cache.json`. Unchanged files from a prior
   run are not re-categorized or re-searched against SharePoint — there is
   no new information to gain from repeating that work, only cost. (The
   cache is only persisted via `--commit` after a run finishes processing
   everything it found — see SKILL.md step 1 — so a crash mid-run can't
   cause a file to be wrongly skipped forever.)
2. **A dedicated small file for "still needs a decision," instead of a
   full-log re-read.** Files logged with action `needs_review` don't need
   re-searching against SharePoint on any schedule — nothing about the
   underlying fact changes on its own. What they do need is to stay
   *visible* to Silas every run without anyone re-reading the whole
   history. `append_log.py` maintains `needs-review.json` automatically
   (add on `needs_review`, remove once a later run resolves the same path)
   specifically so that "what's still waiting on me?" is a cheap read of a
   small file, not a scan of `log.jsonl`.
3. **A rolling log summary, not an ever-growing one.** `append_log.py`
   keeps the full history in `log.jsonl` (append-only, for audit purposes)
   but regenerates `log-summary.md` to hold only the last 8 runs. Claude
   should read `log-summary.md` to get oriented at the start of a run, not
   the full `log.jsonl` — the JSONL is for scripts and for the rare case
   Silas asks "what happened to file X three months ago," not for routine
   context-loading.
4. **One log call per run, not one per file.** SKILL.md step 6 collects
   this run's `scanned`/`categorized`/`matched_duplicate`/`needs_review`
   entries and appends them in a single `append_log.py` call, because that
   script re-reads the entirety of `log.jsonl` once per call to regenerate
   the summary — calling it per-file would make that cost scale with
   Downloads' file count instead of staying flat per run.
5. **Scripts do the deterministic work.** Hashing, diffing, staging files
   to `trash/` with their SharePoint evidence (`stage_for_deletion.py`),
   and purging expired trash are all plain Python (`scripts/`), not
   something Claude reasons through token-by-token each run. Reserve model
   reasoning for the parts that actually need judgment: categorizing
   ambiguous files, weighing SharePoint match confidence, and deciding
   what to ask Silas.

## NotebookLM — a suggestion, not a live integration

Silas mentioned NotebookLM. Worth being precise about what's actually
possible today: **as of this skill's writing (mid-2026), NotebookLM does
not expose a public API** — this is worth re-confirming rather than taking
on faith, since it's the kind of thing that could change without this
document being updated. If it's still true, there is no way for this
skill to call NotebookLM programmatically as part of an automated weekly
run. Anything involving NotebookLM here is a manual, human-in-the-loop
workflow Silas could optionally run himself — not something to build
automation around, and not something to silently assume is wired up.

Where it could genuinely help, if Silas wants to try it by hand:

- **Large reference corpora**, not individual Downloads files. If Ax
  Legal's SharePoint folder structure, client classification rules, or
  past categorization decisions grow into a large body of reference
  material, that's the kind of thing NotebookLM is good at condensing —
  Silas could upload it to a notebook and pull a short summary/FAQ back
  out, which then becomes a much smaller `references/` file for this
  skill to actually consume. NotebookLM's summarization happens outside
  Claude's context window entirely, so it's a way to compress a large
  source down to something cheap to re-read every week — but the
  compression step itself is manual.
- **Not** for individual file triage. Routing a single downloaded PDF
  doesn't benefit from an external summarization tool — that's already
  cheap (see "What's already built in," above), and adding a manual
  round-trip through another tool would slow the workflow down for no
  token savings.

If NotebookLM ever ships an API, revisit this: the natural integration
point would be step 2 (categorization) for files where a full-content read
is otherwise necessary — offload the summarization there, feed the
condensed summary back in instead of the raw file. Until then, the five
structural optimizations above are what actually keep this skill cheap to
run every week, and they don't depend on any tool Silas would have to
operate by hand.
