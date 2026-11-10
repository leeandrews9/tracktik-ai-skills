"""Find every time two roles at one site were on break at the same time, check coverage,
and price the overlap.

    python break_overlap.py --account 101 --role-a "Site Supervisor" --role-b "Assistant Supervisor" \
        --days 90 --rate 38.50 --min-coverage 2 --out out/break-overlap

Writes <out>/overlaps.csv and <out>/summary.json and prints a short summary.
Read-only: GET requests only.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tracktik-api-setup" / "scripts"))
from tracktik_client import TrackTik, local, parse_dt, ref_id, window  # noqa: E402


def roles(arg: str) -> set[str]:
    return {r.strip().lower() for r in arg.split(",") if r.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", required=True, help="TrackTik site (account) id")
    ap.add_argument("--role-a", required=True, help="Position name(s), comma-separated, exact match (case-insensitive)")
    ap.add_argument("--role-b", required=True, help="Position name(s) for the other role")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--break-type", default="MEAL", help="MEAL, REST, BREAK or ALL")
    ap.add_argument("--rate", type=float, help="Hourly bill rate used to price the overlap (usually role B's rate)")
    ap.add_argument("--min-coverage", type=int, default=1,
                    help="Minimum other officers that must be on post during an overlap")
    ap.add_argument("--out", default="out/break-overlap")
    a = ap.parse_args()

    tt = TrackTik()
    start, end = window(tt, a.days)
    acct = str(a.account)

    positions = {p["id"]: p for p in tt.all("/positions", {"account": acct, "includeInactive": "true"})
                 if str(ref_id(p.get("account"))) == acct}
    if not positions:
        sys.exit(f"No positions found for account {acct}.")
    names = {pid: (p.get("name") or "").strip() for pid, p in positions.items()}
    ra, rb = roles(a.role_a), roles(a.role_b)
    missing = [r for r in ra | rb if r not in {n.lower() for n in names.values()}]
    if missing:
        sys.exit(f"Role(s) not found at this site: {missing}. Positions here: {sorted(set(names.values()))}")

    # Work sessions = actual punches. Epoch filters on startedOn work; account is re-checked client-side.
    f = {"startedOn:gte": int(start.timestamp()), "startedOn:lte": int(end.timestamp())}
    tt.check_filter("/work-sessions", f)
    sessions = [w for w in tt.all("/work-sessions", f) if str(ref_id(w.get("account"))) == acct]
    ws = {w["id"]: w for w in sessions}

    tt.check_filter("/break-sessions", f)
    breaks = [b for b in tt.all("/break-sessions", f)
              if ref_id(b.get("workSession")) in ws
              and (a.break_type.upper() == "ALL" or b.get("type") == a.break_type.upper())]

    def role_of(b):
        return names.get(ref_id(ws[ref_id(b["workSession"])].get("position")), "").lower()

    open_breaks = [b for b in breaks if not b.get("endDateTime")]
    closed = [b for b in breaks if b.get("endDateTime")]
    A = [b for b in closed if role_of(b) in ra]
    B = [b for b in closed if role_of(b) in rb]

    # breaks by employee, for coverage checks
    breaks_by_emp = defaultdict(list)
    for b in closed:
        breaks_by_emp[ref_id(b["employee"])].append((parse_dt(b["startDateTime"]), parse_dt(b["endDateTime"])))

    rows = []
    for x in A:
        xs, xe = parse_dt(x["startDateTime"]), parse_dt(x["endDateTime"])
        for y in B:
            if ref_id(x["employee"]) == ref_id(y["employee"]):
                continue
            ys, ye = parse_dt(y["startDateTime"]), parse_dt(y["endDateTime"])
            os_, oe = max(xs, ys), min(xe, ye)
            if oe <= os_:
                continue
            mins = round((oe - os_).total_seconds() / 60, 1)
            excluded = {ref_id(x["employee"]), ref_id(y["employee"])}
            on_post = []
            for w in sessions:
                emp = ref_id(w.get("employee"))
                if emp in excluded:
                    continue
                ws_s, ws_e = parse_dt(w["startDateTime"]), parse_dt(w.get("endDateTime")) or end
                if not (ws_s <= os_ and ws_e >= oe):
                    continue   # not clocked in for the whole overlap
                if any(bs < oe and be > os_ for bs, be in breaks_by_emp.get(emp, [])):
                    continue   # was on their own break during it
                on_post.append(names.get(ref_id(w.get("position")), "?"))
            rows.append({
                "date": local(os_).date().isoformat(),
                "overlap_start": local(os_).strftime("%H:%M"),
                "overlap_end": local(oe).strftime("%H:%M"),
                "overlap_minutes": mins,
                "role_a": role_of(x), "role_a_break": f"{local(xs):%H:%M}-{local(xe):%H:%M}",
                "role_b": role_of(y), "role_b_break": f"{local(ys):%H:%M}-{local(ye):%H:%M}",
                "officers_on_post": len(on_post),
                "on_post_positions": "; ".join(sorted(on_post)),
                "coverage_ok": len(on_post) >= a.min_coverage,
                "credit": round(mins / 60 * a.rate, 2) if a.rate else None,
            })
    rows.sort(key=lambda r: (r["date"], r["overlap_start"]))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out / "overlaps.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    days_worked_both = len({local(parse_dt(x["startDateTime"])).date() for x in A} &
                           {local(parse_dt(y["startDateTime"])).date() for y in B})
    total_min = round(sum(r["overlap_minutes"] for r in rows), 1)
    summary = {
        "site": acct, "window": [start.date().isoformat(), end.date().isoformat()],
        "role_a": sorted(ra), "role_b": sorted(rb), "break_type": a.break_type.upper(),
        "days_both_roles_took_breaks": days_worked_both,
        "overlap_events": len(rows),
        "overlap_days": len({r["date"] for r in rows}),
        "total_overlap_minutes": total_min,
        "total_overlap_hours": round(total_min / 60, 2),
        "min_officers_on_post_during_overlap": min((r["officers_on_post"] for r in rows), default=None),
        "events_below_min_coverage": sum(1 for r in rows if not r["coverage_ok"]),
        "min_coverage_required": a.min_coverage,
        "rate": a.rate,
        "credit_total": round(sum(r["credit"] or 0 for r in rows), 2) if a.rate else None,
        "open_breaks_excluded": len(open_breaks),
        "first_overlap": rows[0]["date"] if rows else None,
        "last_overlap": rows[-1]["date"] if rows else None,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    written = f"{out / 'overlaps.csv'} and " if rows else ""
    print(f"\nWrote {written}{out / 'summary.json'}  ({tt.requests} API requests)")


if __name__ == "__main__":
    main()
