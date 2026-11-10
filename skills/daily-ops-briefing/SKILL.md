---
name: daily-ops-briefing
description: Write the morning operations briefing from TrackTik. It covers what happened overnight across all sites (incidents, dispatches, anything still open, vacant posts and no-shows) so ops leads can start the day knowing what needs attention. Use this whenever someone asks what happened last night or overnight, wants a morning briefing, shift recap, overnight summary or start-of-day report, or asks "anything I need to know this morning".
---

# Daily ops briefing

**Tier 1**: read-only. It summarises; it doesn't contact anyone or change anything.

## Run it

```
python skills/daily-ops-briefing/scripts/overnight_pull.py --out out/briefing
python skills/daily-ops-briefing/scripts/overnight_pull.py --since 2026-11-08T18:00 --until 2026-11-09T07:00
```

Default window: 18:00 yesterday to now. Output: `overnight.json` with counts, incidents (with summary text),
dispatches, vacant posts and no-shows.

Demo: `TT_FIXTURES=fixtures` (there was a fire at Westgate last night).

## Write the briefing

Keep it under a page, and put the most important item first. Use this structure:

```
OVERNIGHT BRIEFING - <date>  (<window>)

NEEDS ACTION NOW
- <open dispatches, coverage gaps right now, anything high severity without a follow-up>

INCIDENTS (<n>)
- <Site> - <Location> - <Type> at <time>: one-line summary. <Status>

COVERAGE
- Vacant posts: <site / position / time>  (or "None")
- No-shows: <site / position / time>      (or "None")

DISPATCHES: <n> total, <n> still open
- <only the notable ones>

QUIET SITES: <list or "all other sites quiet">
```

Rules:
- **Severity first.** Fire, medical, injuries, police response and property damage go at the top, even if there's
  only one of them.
- **Open items are action items.** A dispatch with no `closed` time and a vacant post that's still uncovered both
  belong under NEEDS ACTION NOW.
- Use the report's own summary text; don't embellish. If a summary is missing, say "no narrative entered". That's
  a supervisor follow-up.
- Don't include officer names unless the ops lead asks. Position and site are enough for a briefing.
- If everything is quiet, say so in one line. A short briefing is a good briefing.

## Make it a habit

This is the easiest skill to automate: run it on a schedule at 06:30 and post the result to your ops channel in
Teams or Slack. Because it only reads and summarises, it's a safe first agent to let run on its own.
