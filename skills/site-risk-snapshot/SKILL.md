---
name: site-risk-snapshot
description: Build a one-page risk snapshot for a client site from TrackTik data, covering incident rate per 1,000 staffed hours, trend against the prior period, incident mix, where and when incidents happen, and a transparent 0-100 indicator score, for quarterly business reviews (QBRs), renewals and security-gap conversations. Use this whenever someone asks for a QBR, client review, site risk assessment, security assessment, site health check, "how is this site trending", or wants data to support a recommendation for more coverage, cameras or patrols.
---

# Site risk snapshot

Clients rarely see their own incident data organised. A one-page snapshot every quarter gives the account manager
something real to talk about, and it surfaces upgrades the data actually supports.

**Tier 1** to build (read-only). **Tier 3** to share: a person reviews it before it goes to the client.

## Run it

```
python skills/site-risk-snapshot/scripts/site_risk.py --account 102 --days 90 --out out/site-risk
```

Demo: `TT_FIXTURES=fixtures` with `--account 102`.

`site_risk.json` contains: incidents, staffed hours, incidents per 1,000 hours (this period and the last), breakdown
by type, location, time of day and month, and the indicator score with each component shown.

## The indicator score

0-100, higher means more attention needed. It's a **weighted blend of five indicators**, each scored against cut
points set at the top of `site_risk.py`:

| Indicator | Weight | Why |
|---|---|---|
| Incidents per 1,000 staffed hours | 35% | Activity normalised for how much coverage the site has |
| Trend vs prior period | 20% | Is it getting better or worse |
| High-severity share | 25% | Fire, medical, assault, break-in and similar count for more |
| Concentration at one location | 10% | A fixable hotspot |
| Overnight share | 10% | When risk is highest and staffing is thinnest |

The cut points are starting assumptions. Tune them once you've run the snapshot across your own portfolio, and
always show the components next to the score. A number without its reasons doesn't earn trust.

## One-page layout

1. **Headline**: one sentence ("Incidents down 18% on last quarter; most remaining activity is overnight at the loading dock").
2. **Numbers**: incidents, rate per 1,000 hours, change, score.
3. **What's driving it**: top 3 types, top 2 locations, time-of-day pattern.
4. **What we did this quarter**: from the account manager. Ask; don't invent.
5. **Recommendation**: one or two, tied directly to the pattern (for example, an overnight hotspot at the loading
   dock → camera or added patrol checkpoint).

## What this version doesn't include

TrackTik shows what your officers saw. A full site risk assessment also brings in **the world around the site**:
local crime data, FEMA and natural-hazard data, FBI crime statistics, industry benchmarks, and a score history
across quarters, so the client can watch their risk come down. The JSON lists these under `not_included`. Say so
when you present it, so nobody mistakes this for a full assessment.

## Limits

- Incident counts depend on officers reporting consistently. A site with great officers can look "riskier" than
  one where nobody writes reports.
- If staffed hours are 0 for the prior period (new site, or punching started recently), the trend is skipped.
