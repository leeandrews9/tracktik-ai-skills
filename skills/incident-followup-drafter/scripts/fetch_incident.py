"""Collect everything needed to draft a client follow-up for one incident.

    python fetch_incident.py --report 40096 --out out/incident
    python fetch_incident.py --account 103 --latest --out out/incident

Writes <out>/incident.json. Confidential and admin-only report fields are separated out so they
are never copied into a client-facing draft. Read-only: GET requests only.
"""
import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tracktik-api-setup" / "scripts"))
from tracktik_client import TrackTik, local, ref_id  # noqa: E402


def val(field):
    v = field.get("value")
    return v.get("value") if isinstance(v, dict) else v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", help="Report id")
    ap.add_argument("--account", help="Site (account) id - use with --latest")
    ap.add_argument("--latest", action="store_true", help="Most recent incident-flagged report at --account")
    ap.add_argument("--days", type=int, default=90, help="Look-back for site history")
    ap.add_argument("--out", default="out/incident")
    a = ap.parse_args()

    tt = TrackTik()
    now = tt.now()
    hist_from = int((now - timedelta(days=a.days)).timestamp())
    history = tt.all("/reports", {"submittedOn:gte": hist_from, "submittedOn:lte": int(now.timestamp()),
                                  "scope": "HAS_INCIDENT"})

    if a.report:
        st, body = tt.get(f"/reports/{a.report}")
        if st != 200:
            sys.exit(f"Report {a.report} not found (HTTP {st}).")
        report = body["data"]
    elif a.account and a.latest:
        mine = [r for r in history if str(ref_id(r.get("account"))) == str(a.account)]
        if not mine:
            sys.exit(f"No incident-flagged reports at account {a.account} in the last {a.days} days.")
        report = max(mine, key=lambda r: r.get("submittedOn") or "")
    else:
        sys.exit("Give --report <id>, or --account <id> --latest.")

    acc_id = ref_id(report.get("account"))
    _, acc = tt.get(f"/accounts/{acc_id}", {"include": "address"})
    acc = acc.get("data", {})
    locs = {x["id"]: x.get("name") for x in tt.all("/site-locations")}
    flags = {x["id"]: x.get("name") for x in tt.all("/report-flags")}

    client_safe, internal = {}, {}
    for f in tt.all("/report-fields", {"report": report["id"], "include": "templateField"}):
        tf = f.get("templateField") or {}
        label = tf.get("label") or f.get("fieldTag") or str(f["id"])
        if f.get("archived") or val(f) in (None, ""):
            continue
        (internal if tf.get("confidential") or tf.get("adminOnly") else client_safe)[label] = val(f)

    dispatch = None
    if report.get("dispatchTask"):
        st, d = tt.get(f"/dispatch-tasks/{ref_id(report['dispatchTask'])}")
        if st == 200:
            d = d["data"]
            dispatch = {"opened": str(local(d.get("startedOn"))), "closed": str(local(d.get("closedOn"))),
                        "priority": d.get("priority"), "instructions": d.get("taskInstructions")}

    loc_id = ref_id(report.get("siteLocation"))
    same_site = [r for r in history if ref_id(r.get("account")) == acc_id and r["id"] != report["id"]]
    post_orders = [{"subject": (p.get("subject") or {}).get("name"), "details": p.get("details")}
                   for p in tt.all("/post-orders", {"account": acc_id, "include": "subject"})
                   if str(ref_id(p.get("account"))) == str(acc_id) and p.get("status", "ACTIVE") == "ACTIVE"]

    out = {
        "report_id": report["id"],
        "site": {"id": acc_id, "name": acc.get("name"), "address": acc.get("address")},
        "location": locs.get(loc_id),
        "incident_type": flags.get(ref_id(report.get("reportFlag"))),
        "occurred": str(local(report.get("reportDateTime") or report.get("submittedOn"))),
        "report_status": report.get("status"),
        "dispatch": dispatch,
        "client_safe_fields": client_safe,
        "INTERNAL_ONLY_do_not_send": internal,
        "site_history": {
            "days": a.days,
            "other_incidents_at_site": len(same_site),
            "other_incidents_same_location": sum(1 for r in same_site if ref_id(r.get("siteLocation")) == loc_id),
            "by_type": {k: v for k, v in sorted(
                {flags.get(ref_id(r.get("reportFlag"))): 0 for r in same_site}.items())},
        },
        "active_post_orders": post_orders,
    }
    for r in same_site:
        out["site_history"]["by_type"][flags.get(ref_id(r.get("reportFlag")))] += 1

    p = Path(a.out)
    p.mkdir(parents=True, exist_ok=True)
    (p / "incident.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("report_id", "site", "location", "incident_type", "occurred")}, indent=2, default=str))
    print(f"client-safe fields: {list(client_safe)}  |  internal-only fields withheld: {list(internal)}")
    print(f"Wrote {p / 'incident.json'}")


if __name__ == "__main__":
    main()
