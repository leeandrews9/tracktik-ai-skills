---
name: dispatch-hotspot-finder
description: Find where and when dispatches and incidents concentrate across TrackTik sites, such as one stairwell, gate or parking level driving a large share of overnight calls, and turn it into a fix you can propose to the client (camera, patrol point, lighting, access change). Use this whenever someone asks which sites or locations have the most dispatches or incidents, where problems keep happening, what's driving overnight calls, why a site is so busy, what to recommend at a site, or wants evidence for a camera, patrol or post change.
---

# Dispatch hotspot finder

**The story behind this skill:** at one property, 36% of overnight dispatches traced back to a single stairwell. One
talk-down camera covering that stairwell fixed most of it. Finding that took one query once the data was in
TrackTik. This skill is that query, for every site at once.

**Tier 1**: read-only analysis. Recommendations are proposals for a person to take to the client.

## Run it

```
python skills/dispatch-hotspot-finder/scripts/hotspots.py --days 90 --overnight 22:00-06:00 --out out/hotspots
python skills/dispatch-hotspot-finder/scripts/hotspots.py --days 90 --account 102 --all-hours
```

Demo: `TT_FIXTURES=fixtures` (Meridian Distribution Center has the stairwell pattern).

Output `hotspots.json` holds, for each site: event count, **share at the top location**, every location's share, and,
for the top location, events by hour, by weekday and by incident type.

## How it works

- Events = dispatch tasks, plus incident-flagged reports that had no dispatch (so nothing is counted twice).
- Location comes from the dispatch's site location, or else from the linked report's `siteLocation`. Many tenants
  dispatch to the account address, so the report is usually where the precise spot lives.
- `location_coverage_pct` = share of events where an officer recorded a location.

## Reading the results

1. **Check location coverage first.** If most events say "(no location recorded)", the finding is about data
   quality, not about a hotspot: officers aren't selecting a Site Location on their reports. Recommend making
   "Site Location / Area" a required field on incident templates and re-running in 60 days. That's worth telling
   the client too: it's a quick operational improvement.
2. **Mind small numbers.** 5 of 10 events at one gate is a lead, not a pattern. Say "early signal" below about 20 events.
3. **Look at the hour and weekday spread** for the top location. "Fri/Sat 01:00-03:00 at the stairwell" points to
   a different fix than "every night at shift change".
4. **Look at the incident types.** Trespass and loitering point to access control and deterrence. Vandalism points
   to cameras and lighting. Medical points to something else entirely.

## Turning a hotspot into a recommendation

Write it as a short note the account manager can send:

> Over the last [N] days, **[X]%** of overnight calls at [Site] came from **[Location]**, mostly [types] between
> [hours]. We recommend [one specific fix: a talk-down camera covering the stairwell door / adding it as a patrol
> checkpoint every hour / a lock or alarm on the door / lighting]. We'll track the share of calls from that spot for
> the next 60 days so you can see whether it worked.

Pick **one** fix that matches the pattern. Don't quote prices. Pricing is a conversation for a person to have.

## Limits

- Hotspots are only as good as the location data officers enter.
- Dispatch volume also reflects how often the client calls. A busy site isn't necessarily a dangerous one.
