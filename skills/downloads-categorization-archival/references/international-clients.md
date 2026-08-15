# International Clients & the "Allocate Properly" Folder

## Why this exists

Ax Legal serves both Brazilian and international clients. Files tied to an
international client are the ones this skill is allowed to route
automatically to a shared `Allocate Properly` folder at the SharePoint
root, without asking Silas each time, once they've cleared the SharePoint
duplicate check with no match. Files tied to a domestic client, or any
client that hasn't been explicitly classified, always fall through to
"ask Silas" instead.

## This list is learned, not assumed

Do **not** guess whether a client is international from their name, the
language of a document, or any other proxy. Names are not reliable signals
of a client's jurisdiction or the classification Ax Legal actually uses
internally, and guessing wrong here means a client's documents end up in
the wrong SharePoint location.

Instead:

1. The live mapping lives in `~/.downloads-maintenance/international-clients.json`
   — a simple `{ "client name": true | false }` map — not in this repo. It's
   per-user runtime state that grows over time, seeded empty. If the file
   is missing or fails to parse, treat it as empty and re-ask Silas about
   any client that comes up — never fall back to guessing from a partial
   or corrupted read, and never treat "unparseable" as "no international
   clients" (that would silently misroute files that were previously
   confirmed international).
2. The first time a file is clearly tied to a client name that isn't yet a
   key in that file, ask Silas directly: "Is `<client>` one of Ax Legal's
   international clients?" A yes/no question, once. Persist the answer.
3. From then on, that client is resolved automatically — international
   clients route to `Allocate Properly` (after a confirmed no-match on the
   duplicate check), everyone else routes to "ask Silas where this goes."

## Creating the "Allocate Properly" folder

Create it once, at the root of the Ax Legal SharePoint site, the first time
a run actually needs to upload something into it — don't pre-create it
speculatively. After creating it (or finding it already exists), cache its
folder ID/URL in `~/.downloads-maintenance/sharepoint-cache.json` so future
runs don't re-resolve it.

## Example seed (illustrative only — do not copy real client names into
this repo file; this file is version-controlled and world-readable within
the skill, the live list in `~/.downloads-maintenance/` is not)

```json
{
  "example-client-a": true,
  "example-client-b": false
}
```
