"""Find which sites, hours and (where configured) spots inside a site drive dispatches and incidents.

    python hotspots.py --days 90 --overnight 22:00-06:00 --out out/hotspots
    python hotspots.py --days 90 --account 102 --all-hours

Every report and dispatch is tied to its site (account). Sites that also have Site Locations set up
(named spots inside the site: a stairwell, gate, dock) get a within-site breakdown too.

Writes <out>/hotspots.json and prints a ranked summary. Read-only: GET requests only.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tracktik-api-setup" / "scripts"))
from tracktik_client import TrackTik, local, ref_id, window  # noqa: E402


def in_window(dt, start_hm, end_hm):
    m = dt.hour * 60 + dt.minute
    s = int(start_hm[:2]) * 60 + int(start_hm[3:])
    e = int(end_hm[:2]) * 60 + int(end_hm[3:])
    return (s <= m < e) if s < e else (m >= s or m < e)   # handles windows that cross midnight


def profile(ev):
    return {"by_hour": dict(sorted(Counter(e["when"].hour for e in ev).items())),
            "by_weekday": dict(Counter(e["when"].strftime("%a") for e in ev).most_common()),
            "by_type": dict(Counter(e["flag"] or "(none)" for e in ev).most_common())}


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
    site_locs = tt.all("/site-locations")
    locs = {x["id"]: x.get("name") for x in site_locs}
    accts_with_locs = {ref_id(x.get("account")) for x in site_locs}
    flags = {x["id"]: x.get("name") for x in tt.all("/report-flags")}

    tt.check_filter("/dispatch-tasks", f)
    dispatches = tt.all("/dispatch-tasks", f)
    # /reports REQUIRES a date filter (400 without one) and only honours submittedOn.
    reports = tt.all("/reports", {"submittedOn:gte": int(start.timestamp()), "submittedOn:lte": int(end.timestamp())})
    report_by_id = {r["id"]: r for r in reports}

    events = []   # one row per dispatch, plus incident reports that had no dispatch
    for d in dispatches:
        rep = report_by_id.get(ref_id(d.get("report")))
        # Dispatches often point at the site address; a spot inside the site, if any, is on the linked report.
        loc = ref_id(d.get("location")) if d.get("locationType") == "SITE_LOCATION" else None
        loc = loc or (ref_id(rep.get("siteLocation")) if rep else None)
        events.append({"kind": "dispatch", "account": ref_id(d.get("account")), "location": locs.get(loc),
                       "when": local(d.get("startDateTime") or d.get("startedOn")),
                       "flag": flags.get(ref_id(rep.get("reportFlag"))) if rep else None,
                       "report": ref_id(d.get("report"))})
    for r in reports:
        if r.get("reportFlag") and not r.get("dispatchTask"):
            events.append({"kind": "incident", "account": ref_id(r.get("account")),
                           "location": locs.get(ref_id(r.get("siteLocation"))),
                           "when": local(r.get("reportDateTime") or r.get("submittedOn")),
                           "flag": flags.get(ref_id(r.get("reportFlag"))), "report": r["id"]})

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
        row = {"account": acc, "site": accounts.get(acc, {}).get("name", str(acc)),
               "events": len(ev), "share_of_all_events_pct": round(100 * len(ev) / len(events), 1),
               "dispatches": sum(1 for e in ev if e["kind"] == "dispatch"),
               "site_profile": profile(ev),
               "site_locations_configured": acc in accts_with_locs,
               "report_ids_for_narrative_review": [e["report"] for e in ev if e["report"]][:50],
               "first": min(e["when"] for e in ev).date().isoformat(),
               "last": max(e["when"] for e in ev).date().isoformat()}
        located = [e for e in ev if e["location"]]
        if located:
            counts = Counter(e["location"] for e in located)
            top, n = counts.most_common(1)[0]
            row.update({
                "events_with_site_location": len(located),
                "top_location": top, "top_location_events": n,
                "top_location_share_pct": round(100 * n / len(ev), 1),
                "locations": [{"location": k, "events": c, "share_pct": round(100 * c / len(ev), 1)}
                              for k, c in counts.most_common()],
                "top_location_profile": profile([e for e in ev if e["location"] == top]),
            })
        sites.append(row)
    sites.sort(key=lambda s: -s["events"])

    result = {"window": [start.date().isoformat(), end.date().isoformat()],
              "time_filter": "all hours" if a.all_hours else a.overnight,
              "total_events": len(events), "sites": sites,
              "notes": ["events = dispatch tasks + incident-flagged reports that had no dispatch",
                        "every event is tied to its site; a within-site breakdown needs Site Locations configured",
                        f"sites with fewer than {a.min_events} events are left out"]}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hotspots.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"{result['time_filter']} events, {result['window'][0]} to {result['window'][1]}: {len(events)}\n")
    for s in sites:
        hour, cnt = max(s["site_profile"]["by_hour"].items(), key=lambda kv: kv[1])
        print(f"{s['site']}: {s['events']} events ({s['share_of_all_events_pct']}% of all) - "
              f"busiest hour {hour:02d}:00 ({cnt})")
        if s.get("top_location"):
            print(f"    {s['top_location_share_pct']}% at {s['top_location']} ({s['top_location_events']})")
            for l in s["locations"][1:3]:
                print(f"    {l['location']}: {l['share_pct']}%")
    print(f"\nWrote {out / 'hotspots.json'}")


if __name__ == "__main__":
    main()
