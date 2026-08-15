# Weekly Wednesday Scheduling

## Mechanism

Use the `create_trigger` tool (Claude Code Remote / CCR environment) to
create a Routine that fires into the current session every Wednesday. Bind
it to this session (the default targeting mode — no `persistent_session_id`
or `create_new_session_on_fire` needed) so the weekly run continues the
same conversation Silas already has context in, rather than starting cold
each time.

```
create_trigger(
  name: "Weekly Downloads maintenance",
  prompt: "Run the downloads-categorization-archival skill: scan ~/Downloads,
           categorize, check Ax Legal SharePoint for duplicates, stage
           confirmed duplicates for deletion, route international-client
           files with no SharePoint match to Allocate Properly, and leave
           everything else for review. Report a short summary.",
  cron_expression: "0 12 * * 3"
)
```

## Cron expression and timezone

`create_trigger` cron is evaluated in **UTC**. `0 12 * * 3` means Wednesday
12:00 UTC, which is 09:00 in São Paulo (UTC-3, no DST currently observed in
Brazil). **This is a default assumption — confirm the actual desired local
time and timezone with Silas before creating the trigger**, don't create it
silently. If he wants a different day/time, recompute the UTC hour from his
stated local time and adjust the day-of-week field too if the conversion
crosses midnight (e.g. a late-evening local time the day before would shift
the UTC day forward).

## Why unattended runs must be conservative

A weekly trigger fires with nobody watching. `AskUserQuestion` has no one
to answer it in that context. That's why SKILL.md step 4 splits behavior:
interactive sessions can ask synchronously, but the unattended weekly run
must never block on a question — anything that would need one just gets
logged to `needs-review` and surfaced in the run's summary for Silas to see
whenever he next opens the conversation. The trigger binds to this session
specifically so that summary lands somewhere Silas will actually see it.

## Maintaining the trigger

- `list_triggers` to find the trigger ID if it's no longer in context.
- `update_trigger` to change the day/time or pause it (`enabled: false`)
  without losing run history — prefer this over delete+recreate.
- `delete_trigger` only if Silas wants the weekly run gone for good.
