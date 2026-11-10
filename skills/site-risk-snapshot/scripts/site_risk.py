"""Build a TrackTik-only risk snapshot for one site: incident rate, trend, where and when,
and a transparent 0-100 indicator score.

    python site_risk.py --account 102 --days 90 --out out/site-risk

Writes <out>/site_risk.json. Read-only: GET requests only.
The score uses ONLY TrackTik data. It is a conversation starter, not an actuarial risk rating.
"""
import argparse
import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tracktik-api-setup" / "scripts"))
from tracktik_client import TrackTik, local, parse_dt, ref_id  # noqa: E402

# Incident types treated as high severity. Edit to match your own report flags.
HIGH_SEVERITY = {"fire", "medical", "assault", "weapon", "burglary", "robbery", "break-in",
                 "unauthorized access", "vandalism", "theft", "workplace violence"}


def daypart(h):
    return "overnight (22-06)" if h >= 22 or h < 6 else "day (06-14)" if h < 14 else "evening (14-22)"


def pull_period(tt, acc, start, end):
    s, e = int(start.timestamp()), int(end.timestamp())
    reports = [r for r in tt.all("/reports", {"submittedOn:gte": s, "submittedOn:lte": e, "scope": "HAS_INCIDENT"})
               if str(ref_id(r.get("account"))) == acc]
    sessions = [w for w in tt.all("/work-sessions", {"startedOn:gte": s, "startedOn:lte": e})
                if str(ref_id(w.get("account"))) == acc]
    hours = sum(((parse_dt(w.get("endDateTime")) or end) - parse_dt(w["startDateTime"])).total_seconds() / 3600
                for w in sessions if w.get("startDateTime"))
    dispatches = [d for d in tt.all("/dispatch-tasks", {"startedOn:gte": s, "startedOn:lte": e})
                  if str(ref_id(d.get("account"))) == acc]
    return reports, hours, dispatches


def band(value, cuts):
    """Map a value onto 0-100 using ascending cut points (each cut adds an equal step)."""
    if value is None:
        return None
    return round(100 * sum(value > c for c in cuts) / len(cuts))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", required=True)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--out", default="out/site-risk")
    a = ap.parse_args()

    tt = TrackTik()
    acc = str(a.account)
    end = tt.now()
    start, prev_start = end - timedelta(days=a.days), end - timedelta(days=2 * a.days)
    _, site = tt.get(f"/accounts/{acc}", {"include": "address"})
    site = site.get("data", {})
    locs = {x["id"]: x.get("name") for x in tt.all("/site-locations")}
    flags = {x["id"]: x.get("name") for x in tt.all("/report-flags")}

    cur, cur_hours, cur_disp = pull_period(tt, acc, start, end)
    prev, prev_hours, _ = pull_period(tt, acc, prev_start, start)

    def rate(n, h):
        return round(1000 * n / h, 2) if h else None

    types = Counter(flags.get(ref_id(r.get("reportFlag")), "Unknown") for r in cur)
    where = Counter(locs.get(ref_id(r.get("siteLocation")), "(no location)") for r in cur)
    when = Counter(daypart(local(r.get("reportDateTime") or r.get("submittedOn")).hour) for r in cur)
    months = Counter(local(r.get("reportDateTime") or r.get("submittedOn")).strftime("%Y-%m") for r in cur)
    high = sum(n for t, n in types.items() if t.lower() in HIGH_SEVERITY)

    cur_rate, prev_rate = rate(len(cur), cur_hours), rate(len(prev), prev_hours)
    trend = round(100 * (cur_rate - prev_rate) / prev_rate, 1) if cur_rate is not None and prev_rate else None
    top_share = round(100 * where.most_common(1)[0][1] / len(cur), 1) if cur else 0
    overnight_share = round(100 * when.get("overnight (22-06)", 0) / len(cur), 1) if cur else 0
    high_share = round(100 * high / len(cur), 1) if cur else 0

    # Transparent indicator score. Cut points are starting assumptions - tune them to your portfolio.
    parts = {
        "incident_rate_per_1k_hours": (cur_rate, band(cur_rate, [2, 5, 10, 20]), 0.35),
        "trend_vs_prior_period_pct": (trend, band(trend, [-10, 0, 15, 40]), 0.20),
        "high_severity_share_pct": (high_share, band(high_share, [5, 15, 30, 50]), 0.25),
        "top_location_share_pct": (top_share, band(top_share, [20, 30, 45, 60]), 0.10),
        "overnight_share_pct": (overnight_share, band(overnight_share, [25, 40, 55, 70]), 0.10),
    }
    usable = {k: v for k, v in parts.items() if v[1] is not None}
    wsum = sum(w for _, _, w in usable.values())
    score = round(sum(s * w for _, s, w in usable.values()) / wsum) if wsum else None

    out = {
        "site": {"id": acc, "name": site.get("name"), "address": site.get("address")},
        "window": [start.date().isoformat(), end.date().isoformat()],
        "incidents": len(cur), "staffed_hours": round(cur_hours, 1), "dispatches": len(cur_disp),
        "incidents_per_1k_hours": cur_rate,
        "prior_period": {"incidents": len(prev), "staffed_hours": round(prev_hours, 1), "incidents_per_1k_hours": prev_rate},
        "by_type": dict(types.most_common()), "by_location": dict(where.most_common()),
        "by_daypart": dict(when.most_common()), "by_month": dict(sorted(months.items())),
        "indicator_score_0_100": score,
        "indicators": {k: {"value": v, "points_0_100": s, "weight": w} for k, (v, s, w) in parts.items()},
        "not_included": ["local crime data", "FEMA / natural-hazard data", "FBI UCR data",
                         "client-industry benchmarks", "score history across quarters"],
    }
    p = Path(a.out)
    p.mkdir(parents=True, exist_ok=True)
    (p / "site_risk.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("site", "incidents", "incidents_per_1k_hours", "indicator_score_0_100")},
                     indent=2, default=str))
    if not prev_hours:
        print("Note: no staffed hours in the prior period, so the trend indicator was skipped.")
    print(f"Wrote {p / 'site_risk.json'}")


if __name__ == "__main__":
    main()
