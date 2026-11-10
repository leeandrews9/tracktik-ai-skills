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

Output `hotspots.json` holds, for each site: event count, share of all events, and a profile by hour, weekday and
incident type. For sites that have **Site Locations** set up, it also gives each location's share and a profile of
the top location.

## How it works

- Events = dispatch tasks, plus incident-flagged reports that had no dispatch (so nothing is counted twice).
- **Every event is tied to its site** (the account it was filed from), so the site-level ranking always works.
- **Site Locations** are optional named spots *inside* a site (a stairwell, gate or dock) that an admin sets up
  per site. Where they exist, the event's location comes from the dispatch, or else from the linked report's
  `siteLocation`. Sites without them get no within-site breakdown, and that's normal, not a data problem.

## Reading the results

1. **Start with the site ranking.** Which sites carry most of the overnight load, and at what hours?
2. **Drill into the spot inside the site:**
   - If the site has Site Locations, use `locations` and `top_location_profile`.
   - If it doesn't, read the incident narratives for the busiest site. `report_ids_for_narrative_review` lists
     them; fetch `/report-fields?report=<id>&include=templateField` and look for places mentioned again and
     again ("stairwell B", "the rear gate"). Count the mentions and quote a few.
3. **Mind small numbers.** 5 of 10 events at one gate is a lead, not a pattern. Say "early signal" below about 20 events.
4. **Look at the hour and weekday spread.** "Fri/Sat 01:00-03:00 at the stairwell" points to a different fix than
   "every night at shift change".
5. **Look at the incident types.** Trespass and loitering point to access control and deterrence. Vandalism points
   to cameras and lighting. Medical points to something else entirely.
6. **Optional tip:** if your sites have obvious trouble spots, set them up as Site Locations so future reports
   capture the spot directly and this analysis no longer needs the narratives.

## Turning a hotspot into a recommendation

Write it as a short note the account manager can send:

> Over the last [N] days, **[X]%** of overnight calls at [Site] came from **[Location]**, mostly [types] between
> [hours]. We recommend [one specific fix: a talk-down camera covering the stairwell door / adding it as a patrol
> checkpoint every hour / a lock or alarm on the door / lighting]. We'll track the share of calls from that spot for
> the next 60 days so you can see whether it worked.

Pick **one** fix that matches the pattern. Don't quote prices. Pricing is a conversation for a person to have.

## Limits

- Within-site hotspots need either Site Locations or descriptive narratives. Site-level results don't.
- Dispatch volume also reflects how often the client calls. A busy site isn't necessarily a dangerous one.
