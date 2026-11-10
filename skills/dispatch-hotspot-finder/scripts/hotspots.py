"""Find where (and when) dispatches and incidents concentrate.

    python hotspots.py --days 90 --overnight 22:00-06:00 --out out/hotspots
    python hotspots.py --days 90 --account 102 --all-hours

Writes <out>/hotspots.json and prints a ranked summary. Read-only: GET requests only.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tracktik-api-setup" / "scripts"))
from tracktik_client import TrackTik, local, ref_id, window  # noqa: E402


NOLOC = "(no location recorded)"


def in_window(dt, start_hm, end_hm):
    m = dt.hour * 60 + dt.minute
    s = int(start_hm[:2]) * 60 + int(start_hm[3:])
    e = int(end_hm[:2]) * 60 + int(end_hm[3:])
    return (s <= m < e) if s < e else (m >= s or m < e)   # handles windows that cross midnight


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--account", help="Limit to one site (account id)")
    ap.add_argument("--overnight", default="22:00-06:00", help="Local time window HH:MM-HH:MM")
    ap.add_argument("--all-hours", action="store_true", help="Ignore the time window")
    ap.add_argument("--min-events", type=int, default=5, help="Ignore sites with fewer events")
    ap.add_argument("--out", default="out/hotspots")
    a = ap.parse_args()

    tt = TrackTik()
    start, end = window(tt, a.days)
    ws, we = a.overnight.split("-")
    f = {"startedOn:gte": int(start.timestamp()), "startedOn:lte": int(end.timestamp())}

    accounts = {x["id"]: x for x in tt.all("/accounts", {"includeInactive": "true"})}
    locs = {x["id"]: x.get("name") for x in tt.all("/site-locations")}
    flags = {x["id"]: x.get("name") for x in tt.all("/report-flags")}

    tt.check_filter("/dispatch-tasks", f)
    dispatches = tt.all("/dispatch-tasks", f)
    # /reports REQUIRES a date filter (400 without one) and only honours submittedOn.
    reports = tt.all("/reports", {"submittedOn:gte": int(start.timestamp()), "submittedOn:lte": int(end.timestamp())})
    report_by_id = {r["id"]: r for r in reports}

    events = []   # one row per dispatch, plus incident reports that had no dispatch
    for d in dispatches:
        when = local(d.get("startDateTime") or d.get("startedOn"))
        rep = report_by_id.get(ref_id(d.get("report")))
        # Many tenants dispatch to the ACCOUNT_ADDRESS, so the precise spot lives on the linked report.
        loc = ref_id(d.get("location")) if d.get("locationType") == "SITE_LOCATION" else None
        loc = loc or (ref_id(rep.get("siteLocation")) if rep else None)
        events.append({"kind": "dispatch", "account": ref_id(d.get("account")), "location": locs.get(loc, NOLOC),
                       "when": when, "flag": flags.get(ref_id(rep.get("reportFlag"))) if rep else None,
                       "priority": d.get("priority")})
    for r in reports:
        if r.get("reportFlag") and not r.get("dispatchTask"):
            events.append({"kind": "incident", "account": ref_id(r.get("account")),
                           "location": locs.get(ref_id(r.get("siteLocation")), NOLOC),
                           "when": local(r.get("reportDateTime") or r.get("submittedOn")),
                           "flag": flags.get(ref_id(r.get("reportFlag"))), "priority": None})

    if a.account:
        events = [e for e in events if str(e["account"]) == str(a.account)]
    if not a.all_hours:
        events = [e for e in events if e["when"] and in_window(e["when"], ws, we)]

    by_site = defaultdict(list)
    for e in events:
        by_site[e["account"]].append(e)

    sites = []
    for acc, ev in by_site.items():
        if len(ev) < a.min_events:
            continue
        located = [e for e in ev if e["location"] != NOLOC]
        loc_counts = Counter(e["location"] for e in located)
        top_loc, top_n = loc_counts.most_common(1)[0] if located else (None, 0)
        at_top = [e for e in ev if e["location"] == top_loc]
        sites.append({
            "account": acc, "site": accounts.get(acc, {}).get("name", str(acc)),
            "events": len(ev), "dispatches": sum(1 for e in ev if e["kind"] == "dispatch"),
            "location_coverage_pct": round(100 * len(located) / len(ev), 1),
            "top_location": top_loc, "top_location_events": top_n,
            "top_location_share_pct": round(100 * top_n / len(ev), 1),
            "top_location_share_of_located_pct": round(100 * top_n / len(located), 1) if located else None,
            "locations": [{"location": k, "events": n, "share_pct": round(100 * n / len(ev), 1)}
                          for k, n in loc_counts.most_common()],
            "top_location_by_hour": dict(sorted(Counter(e["when"].hour for e in at_top).items())),
            "top_location_by_weekday": dict(Counter(e["when"].strftime("%a") for e in at_top).most_common()),
            "top_location_flags": dict(Counter(e["flag"] or "(none)" for e in at_top).most_common()),
            "unlocated_events": len(ev) - len(located),
            "first": min(e["when"] for e in ev).date().isoformat(),
            "last": max(e["when"] for e in ev).date().isoformat(),
        })
    sites.sort(key=lambda s: -(s["top_location_events"] or 0))

    result = {"window": [start.date().isoformat(), end.date().isoformat()],
              "time_filter": "all hours" if a.all_hours else a.overnight,
              "total_events": len(events),
              "location_coverage_pct": round(100 * sum(e["location"] != NOLOC for e in events) / len(events), 1) if events else None,
              "sites": sites,
              "notes": ["events = dispatch tasks + incident-flagged reports that had no dispatch",
                        f"sites with fewer than {a.min_events} events are left out"]}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hotspots.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"{result['time_filter']} events, {result['window'][0]} to {result['window'][1]}: {len(events)} "
          f"(location recorded on {result['location_coverage_pct']}%)\n")
    for s in sites:
        if not s["top_location"]:
            print(f"{s['site']}: {s['events']} events - no locations recorded on any of them")
            continue
        print(f"{s['site']}: {s['events']} events - {s['top_location_share_pct']}% at {s['top_location']} "
              f"({s['top_location_events']}); location recorded on {s['location_coverage_pct']}%")
        for l in s["locations"][1:4]:
            print(f"    {l['location']}: {l['share_pct']}%")
    print(f"\nWrote {out / 'hotspots.json'}")


if __name__ == "__main__":
    main()
