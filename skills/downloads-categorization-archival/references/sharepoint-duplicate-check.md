# SharePoint Duplicate Check

## Goal

Decide, for each new/changed Downloads file, whether an equivalent already
exists somewhere in the Ax Legal SharePoint site. This is the single gate
that decides whether a file is safe to remove locally.

## First run on a machine: resolve the site once

`~/.downloads-maintenance/sharepoint-cache.json` won't exist yet the very
first time this skill runs somewhere. Before searching for any individual
file, resolve and cache the basics:

1. Use `sharepoint_search` (or the equivalent site-listing call available
   through the `ms365` connector) with the query "Ax Legal" to find the
   site. If more than one result plausibly matches, stop and ask Silas
   which one — don't guess between multiple candidates.
2. Record the site's identifier/URL in `sharepoint-cache.json` under a
   `site` key.
3. The `Allocate Properly` folder at the site root won't exist until the
   first file actually needs it (SKILL.md step 4 says not to pre-create it
   speculatively) — resolve/create it lazily and cache its folder ID/URL
   under an `allocate_properly_folder` key at that point.
4. If `sharepoint-cache.json` exists but fails to parse, or a cached
   ID/URL 404s on use (e.g. the folder was renamed or moved in
   SharePoint), don't error out blind — re-resolve once via the same
   search, update the cache, and retry. Only surface an error to Silas if
   re-resolution also fails.

## Tools

Use the `ms365` SharePoint tools:

- `sharepoint_search` — keyword search across the Ax Legal site.
- `sharepoint_folder_search` — search within a specific library/folder
  (use the category from `categorization-policy.md` to narrow the search —
  e.g. search the Tax Documents library first for a file categorized as a
  tax document, instead of searching the whole site blind).

Cache the Ax Legal site identifier and any resolved library/folder paths in
`~/.downloads-maintenance/sharepoint-cache.json` after the first successful
resolution, so every run doesn't re-resolve "which site is Ax Legal" from
scratch.

## Why this can't be a hash comparison

SharePoint search is keyword/metadata based, not content-hash based, and
there's no bulk "give me the SHA-256 of every file in this library" API
available here. So duplicate detection is a judgment call informed by:

1. **Filename match**, after normalizing both sides: strip version/copy
   suffixes (` (1)`, `-copy`, `_final`, `_v2`), extensions, and case.
2. **Size match** (exact or very close — a few bytes of difference from
   metadata embedding is fine, a large difference is not).
3. **Modified/created date proximity** as a tie-breaker signal, not primary
   evidence — files legitimately get re-downloaded weeks after the
   original was filed.

## Confidence levels and what to do with them

- **High confidence** (normalized filename matches closely AND size
  matches closely): treat as a confirmed duplicate. Proceed straight to
  staged deletion (SKILL.md step 5) without asking — this is the case the
  whole workflow exists to handle automatically.
- **Medium confidence** (only one of filename/size matches, or the match
  is a plausible-but-not-exact filename): **treat as not found.** Do not
  delete or guess. Let it fall through to the routing step (SKILL.md step
  4). A false "duplicate" that gets deleted is a much worse failure mode
  than a false "not found" that just leaves a file in Downloads for
  another week.
- **No results**: not found, route per step 4.

**A known, accepted residual risk**: because there's no hash comparison
available, two genuinely different files that happen to share a name and a
similar size could register as a "high confidence" match. This is rare in
practice, and the staged-deletion grace period (SKILL.md step 5) is the
safety net for exactly this case — a wrongly-staged file is still
recoverable from `trash/` for the full grace period, never immediately
gone.

## When the connector isn't available

If `ms365` SharePoint tools aren't reachable (not connected, auth expired,
etc.), stop the run and tell Silas rather than silently treating every file
as "no match found." A connector outage and a genuinely new file look
identical from the "no match" result alone, but they need very different
responses — one needs Silas to reconnect something, the other needs normal
triage.
