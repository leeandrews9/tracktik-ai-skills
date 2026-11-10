"""Pull everything that happened in a time window (default: 18:00 yesterday to now) for the
morning ops briefing.

    python overnight_pull.py                      # last night, all sites
    python overnight_pull.py --since 2026-11-08T18:00 --until 2026-11-09T07:00 --out out/briefing

Writes <out>/overnight.json. Read-only: GET requests only.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tracktik-api-setup" / "scripts"))
from tracktik_client import TZ, TrackTik, local, ref_id  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="Local datetime, e.g. 2026-11-08T18:00 (default 18:00 yesterday)")
    ap.add_argument("--until", help="Local datetime (default now)")
    ap.add_argument("--out", default="out/briefing")
    a = ap.parse_args()

    tt = TrackTik()
    until = datetime.fromisoformat(a.until).replace(tzinfo=TZ) if a.until else tt.now()
    since = (datetime.fromisoformat(a.since).replace(tzinfo=TZ) if a.since
             else (until - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0))
    s, u = int(since.timestamp()), int(until.timestamp())

    accounts = {x["id"]: x.get("name") for x in tt.all("/accounts", {"includeInactive": "true"})}
    locs = {x["id"]: x.get("name") for x in tt.all("/site-locations")}
    flags = {x["id"]: x.get("name") for x in tt.all("/report-flags")}
    positions = {x["id"]: x for x in tt.all("/positions", {"includeInactive": "true"})}

    # Reports: date filter is REQUIRED and must be submittedOn (reportDateTime filters are ignored).
    reports = tt.all("/reports", {"submittedOn:gte": s, "submittedOn:lte": u})
    incidents = []
    for r in (r for r in reports if r.get("reportFlag")):
        fields = tt.all("/report-fields", {"report": r["id"], "include": "templateField"})
        summary = next((ref_val(x) for x in fields
                        if (x.get("templateField") or {}).get("label", "").lower().startswith(("incident summary", "summary", "narrative"))), None)
        incidents.append({"report_id": r["id"], "site": accounts.get(ref_id(r.get("account"))),
                          "location": locs.get(ref_id(r.get("siteLocation"))),
                          "type": flags.get(ref_id(r.get("reportFlag"))),
                          "time": fmt(local(r.get("reportDateTime") or r.get("submittedOn"))),
                          "status": r.get("status"), "summary": summary})

    dispatches = tt.all("/dispatch-tasks", {"startedOn:gte": s, "startedOn:lte": u})
    d_rows = [{"id": d["id"], "site": accounts.get(ref_id(d.get("account"))),
               "location": locs.get(ref_id(d.get("location"))), "priority": d.get("priority"),
               "status": d.get("status"), "opened": fmt(local(d.get("startedOn"))),
               "closed": fmt(local(d.get("closedOn"))), "what": d.get("taskInstructions")} for d in dispatches]

    # Shifts that started in the window: vacant posts and no-shows.
    shifts = tt.all("/shifts", {"startsOn:gte": s, "startsOn:lte": u,
                                "include": "position", "fields": "id,position,employee,startDateTime,endDateTime,vacant,attendanceStatus,status"})
    def shift_row(x):
        p = x.get("position")
        p = p if isinstance(p, dict) else positions.get(p, {})
        return {"shift_id": x["id"], "site": accounts.get(ref_id(p.get("account"))), "position": p.get("name"),
                "start": fmt(local(x.get("startDateTime"))), "end": fmt(local(x.get("endDateTime")))}
    vacant = [shift_row(x) for x in shifts if x.get("vacant")]
    missed = [shift_row(x) for x in shifts if not x.get("vacant") and x.get("attendanceStatus") == "MISSED"]

    out = {
        "window": [fmt(since), fmt(until)],
        "counts": {"reports": len(reports), "incidents": len(incidents), "dispatches": len(d_rows),
                   "dispatches_still_open": sum(1 for d in d_rows if not d["closed"]),
                   "shifts_started": len(shifts), "vacant_posts": len(vacant), "no_shows": len(missed)},
        "incidents_by_type": dict(Counter(i["type"] for i in incidents)),
        "incidents": incidents, "dispatches": d_rows, "vacant_posts": vacant, "no_shows": missed,
    }
    p = Path(a.out)
    p.mkdir(parents=True, exist_ok=True)
    (p / "overnight.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["counts"], indent=2))
    print(f"Wrote {p / 'overnight.json'}")


def ref_val(field):
    v = field.get("value")
    return v.get("value") if isinstance(v, dict) else v


def fmt(d):
    return d.strftime("%Y-%m-%d %H:%M") if d else None


if __name__ == "__main__":
    main()
