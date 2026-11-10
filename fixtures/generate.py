"""Generate the synthetic TrackTik dataset in this folder.

Every company, site, person and event here is FICTIONAL. The data is shaped like real
TrackTik REST responses so the skills run end to end without a tenant:

    python fixtures/generate.py          # rewrites fixtures/*.json (seeded, repeatable)

Built-in stories (so the demos have something to find):
  * Harbor Point Office Park - the Site Supervisor and Assistant Supervisor keep taking
    meal breaks at the same time, while 3 officers stay on post.          -> break-overlap-audit
  * Meridian Distribution Center - about a third of overnight dispatches land on one
    stairwell.                                                            -> dispatch-hotspot-finder
  * Westgate Retail Plaza - a brush fire burned through the rear gate last night.
                                                                          -> daily-ops-briefing,
                                                                             incident-followup-drafter
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).parent
TZ = ZoneInfo("America/Los_Angeles")
NOW = datetime(2026, 11, 9, 7, 0, tzinfo=TZ)   # "this morning" for the demos
DAYS = 90
rnd = random.Random(42)


def iso(d: datetime) -> str:
    return d.astimezone(ZoneInfo("UTC")).isoformat()


def at(day: datetime, hh: int, mm: int = 0) -> datetime:
    return day.replace(hour=hh, minute=mm, second=0, microsecond=0)


# ---------------------------------------------------------------- places
accounts = [
    {"id": 101, "name": "Harbor Point Office Park", "type": "SITE", "customId": "HPOP",
     "address": {"addressLine1": "100 Example Way", "city": "Long Beach", "state": "CA", "postalCode": "90802"},
     "parentAccount": None, "closedDate": None},
    {"id": 102, "name": "Meridian Distribution Center", "type": "SITE", "customId": "MDC",
     "address": {"addressLine1": "200 Sample Blvd", "city": "Ontario", "state": "CA", "postalCode": "91761"},
     "parentAccount": None, "closedDate": None},
    {"id": 103, "name": "Westgate Retail Plaza", "type": "SITE", "customId": "WRP",
     "address": {"addressLine1": "300 Demo Ave", "city": "Riverside", "state": "CA", "postalCode": "92501"},
     "parentAccount": None, "closedDate": None},
]

site_locations = []
loc_id = 500
LOCS = {
    101: ["Main Lobby", "Garage P1", "Loading Dock", "Rooftop Access"],
    102: ["North Stairwell B", "Loading Dock 4", "Main Gate", "Trailer Yard", "Employee Parking", "Break Room"],
    103: ["Rear Gate", "Parking Structure L2", "Food Court", "Storefront Row A"],
}
loc_by_name = {}
for acc, names in LOCS.items():
    for n in names:
        loc_id += 1
        site_locations.append({"id": loc_id, "account": acc, "name": n, "type": "LOCATION",
                               "parent": None, "order": 0, "details": None})
        loc_by_name[(acc, n)] = loc_id

positions = [
    {"id": 201, "account": 101, "name": "Site Supervisor"},
    {"id": 202, "account": 101, "name": "Assistant Supervisor"},
    {"id": 203, "account": 101, "name": "Lobby Officer"},
    {"id": 204, "account": 101, "name": "Patrol Officer"},
    {"id": 205, "account": 101, "name": "Garage Officer"},
    {"id": 211, "account": 102, "name": "Gatehouse Officer (Nights)"},
    {"id": 212, "account": 102, "name": "Patrol Officer (Nights)"},
    {"id": 221, "account": 103, "name": "Patrol Officer (Nights)"},
]

FIRST = ["Alex", "Jordan", "Sam", "Riley", "Casey", "Morgan", "Taylor", "Jamie", "Avery", "Quinn", "Drew", "Rowan"]
LAST = ["Rivera", "Nguyen", "Brooks", "Patel", "Kim", "Lopez", "Carter", "Okafor", "Reyes", "Hayes", "Moreno", "Singh"]
employees = [{"id": 301 + i, "firstName": f, "lastName": l, "status": "ACTIVE"} for i, (f, l) in enumerate(zip(FIRST, LAST))]
# one regular officer per position (index-aligned), plus 4 relief officers
assign = {p["id"]: employees[i]["id"] for i, p in enumerate(positions)}

# ---------------------------------------------------------------- time & breaks
shifts, work_sessions, break_sessions = [], [], []
sid = wid = bid = 10000


def add_shift(pos, emp, start, end, vacant=False, status="APPROVED", attendance="CLOCKED_OUT", breaks=()):
    global sid, wid, bid
    sid += 1
    shifts.append({"id": sid, "position": pos["id"], "employee": None if vacant else emp,
                   "startDateTime": iso(start), "startsOn": iso(start), "endDateTime": iso(end),
                   "vacant": vacant, "status": status, "attendanceStatus": None if vacant else attendance,
                   "plannedDurationHours": round((end - start).seconds / 3600, 2)})
    if vacant or attendance == "MISSED":
        return
    wid += 1
    work_sessions.append({"id": wid, "shift": sid, "position": pos["id"], "account": pos["account"], "employee": emp,
                          "startDateTime": iso(start), "startedOn": iso(start), "endDateTime": iso(end),
                          "endedOn": iso(end), "status": "CLOSED", "clockInMethod": "SHIFT_APP"})
    for b_start, mins, btype in breaks:
        bid += 1
        break_sessions.append({"id": bid, "workSession": wid, "account": pos["account"], "employee": emp,
                               "type": btype, "status": "CLOSED", "startDateTime": iso(b_start),
                               "startedOn": iso(b_start), "endDateTime": iso(b_start + timedelta(minutes=mins)),
                               "initiationMethod": "SHIFT_APP"})


pos = {p["id"]: p for p in positions}
for d in range(DAYS, 0, -1):
    day = (NOW - timedelta(days=d)).replace(hour=0, minute=0)
    if day.weekday() < 5:   # Harbor Point: weekday day shift, 06:00-14:30
        sup_meal = at(day, 11, rnd.choice([0, 15, 30, 45]))
        overlap = rnd.random() < 0.32 and day > NOW - timedelta(days=75)   # the habit started ~10 weeks ago
        asst_meal = sup_meal + timedelta(minutes=rnd.choice([0, 5, 10])) if overlap else at(day, 12, rnd.choice([30, 45]))
        for p_id, meal in ((201, sup_meal), (202, asst_meal), (203, at(day, 10, 0)), (204, at(day, 10, 45)), (205, at(day, 13, 0))):
            add_shift(pos[p_id], assign[p_id], at(day, 6), at(day, 14, 30),
                      breaks=[(meal, 30, "MEAL"), (meal - timedelta(hours=2, minutes=30), 10, "REST")])
    for p_id in (211, 212, 221):   # night posts 22:00-06:30 (last night is added separately below)
        if d == 1:
            continue
        start = at(day, 22)
        add_shift(pos[p_id], assign[p_id], start, start + timedelta(hours=8, minutes=30),
                  breaks=[(start + timedelta(hours=4), 30, "MEAL")])

# last night: one vacant post and one no-show for the briefing
last_night = at(NOW - timedelta(days=1), 22)
add_shift(pos[212], None, last_night, last_night + timedelta(hours=8, minutes=30), vacant=True, status="PUBLISHED")
add_shift(pos[221], assign[221], last_night, last_night + timedelta(hours=8, minutes=30),
          breaks=[(last_night + timedelta(hours=4), 30, "MEAL")])
add_shift(pos[211], employees[10]["id"], last_night, last_night + timedelta(hours=8, minutes=30), attendance="MISSED")

# ---------------------------------------------------------------- dispatches & reports
report_flags = [{"id": 30, "name": "Suspicious Person"}, {"id": 31, "name": "Suspicious Vehicle"},
                {"id": 32, "name": "Trespass"}, {"id": 33, "name": "Loitering"},
                {"id": 34, "name": "Unauthorized Access"}, {"id": 35, "name": "Fire"},
                {"id": 36, "name": "Vandalism"}, {"id": 37, "name": "Medical"}]
report_templates = [{"id": 1, "name": "Daily Activity Report"}, {"id": 2, "name": "Incident Report"},
                    {"id": 3, "name": "Dispatch Response"}]
template_fields = {
    "summary": {"id": 901, "label": "Incident Summary", "type": "TEXTAREA", "confidential": False, "adminOnly": False},
    "action": {"id": 902, "label": "Action Taken", "type": "TEXTAREA", "confidential": False, "adminOnly": False},
    "notified": {"id": 903, "label": "Agencies Notified", "type": "TEXT", "confidential": False, "adminOnly": False},
    "subject": {"id": 904, "label": "Subject Description", "type": "TEXTAREA", "confidential": True, "adminOnly": False},
    "internal": {"id": 905, "label": "Supervisor Internal Notes", "type": "TEXTAREA", "confidential": False, "adminOnly": True},
}
dispatch_tasks, reports, report_fields = [], [], []
did, rid, fid = 7000, 40000, 80000

NARR = {
    "Suspicious Person": ("Officer observed an individual attempting door handles near {loc}. Individual left when approached.",
                          "Officer made contact, individual departed on foot. Area checked, no damage."),
    "Trespass": ("Individual found sleeping in {loc} after hours.", "Officer requested the individual leave; complied without incident."),
    "Loitering": ("Group loitering at {loc} after close.", "Officer advised group of property rules; group dispersed."),
    "Unauthorized Access": ("Door at {loc} found propped open with a wedge.", "Officer removed wedge, secured door, checked the floor."),
    "Vandalism": ("Fresh graffiti found at {loc}.", "Photographed and reported to property management."),
    "Suspicious Vehicle": ("Unfamiliar vehicle idling at {loc} for 20+ minutes.", "Officer logged plate; vehicle departed."),
}


def add_report(acc, loc, flag, when, dispatch=None, summary=None, action=None, notified="None", subject=None, internal=None):
    global rid, fid
    rid += 1
    reports.append({"id": rid, "account": acc, "position": None, "reportTemplate": 2 if flag else 3,
                    "reportFlag": flag["id"] if flag else None, "siteLocation": loc, "status": "APPROVED",
                    "submittedOn": iso(when + timedelta(minutes=25)), "reportDateTime": iso(when),
                    "dispatchTask": dispatch})
    for key, val in (("summary", summary), ("action", action), ("notified", notified), ("subject", subject), ("internal", internal)):
        if val:
            fid += 1
            report_fields.append({"id": fid, "report": rid, "fieldTag": key, "archived": False,
                                  "templateField": template_fields[key], "value": {"value": val}})
    return rid


def add_dispatch(acc, loc_name, when, flag_name):
    global did
    did += 1
    loc = loc_by_name[(acc, loc_name)]
    flag = next(f for f in report_flags if f["name"] == flag_name)
    s, a = NARR.get(flag_name, ("Activity at {loc}.", "Officer responded."))
    r = add_report(acc, loc, flag, when, dispatch=did, summary=s.format(loc=loc_name), action=a)
    dispatch_tasks.append({"id": did, "account": acc, "location": loc, "locationType": "SITE_LOCATION",
                           "priority": rnd.choice(["HIGH", "URGENT", "NORMAL"]), "status": "CLOSED",
                           "startedOn": iso(when), "startDateTime": iso(when),
                           "closedOn": iso(when + timedelta(minutes=rnd.randint(8, 40))),
                           "taskInstructions": f"Respond to {flag_name.lower()} at {loc_name}", "report": r})


def night_time(day):
    return at(day, 22) + timedelta(minutes=rnd.randint(0, 7 * 60 + 30))


# Meridian: ~36% of overnight dispatches at one stairwell
MERIDIAN = ["Loading Dock 4", "Main Gate", "Trailer Yard", "Employee Parking", "Break Room"]
for i in range(56):
    day = (NOW - timedelta(days=rnd.randint(2, DAYS))).replace(hour=0, minute=0)
    stair = i < 20
    add_dispatch(102, "North Stairwell B" if stair else rnd.choice(MERIDIAN), night_time(day),
                 rnd.choice(["Trespass", "Loitering", "Unauthorized Access"]) if stair else rnd.choice(list(NARR)))
# daytime noise at Meridian (should NOT count as overnight)
for i in range(12):
    day = (NOW - timedelta(days=rnd.randint(2, DAYS))).replace(hour=0, minute=0)
    add_dispatch(102, rnd.choice(MERIDIAN), at(day, rnd.randint(9, 16), rnd.randint(0, 59)), rnd.choice(list(NARR)))
# Harbor Point and Westgate: scattered
for acc, n in ((101, 9), (103, 14)):
    for i in range(n):
        day = (NOW - timedelta(days=rnd.randint(2, DAYS))).replace(hour=0, minute=0)
        add_dispatch(acc, rnd.choice(LOCS[acc]), night_time(day) if rnd.random() < .6 else at(day, rnd.randint(8, 18)),
                     rnd.choice(list(NARR)))

# Westgate, last night: the brush fire
fire_at = at(NOW - timedelta(days=1), 23, 48)
did += 1
fire_report = add_report(
    103, loc_by_name[(103, "Rear Gate")], report_flags[5], fire_at, dispatch=did,
    summary=("Officer observed smoke and open flame in the brush strip outside the rear perimeter fence. "
             "Fire spread along the fence line and burned through the rear vehicle gate before the fire "
             "department extinguished it at 00:31. No injuries. Rear gate is not functional and is currently "
             "chained shut."),
    action=("Officer called 911 at 23:49, notified the account manager and property management at 23:55, kept "
            "people clear of the area and met the fire department at the front entrance. Officer remained posted at "
            "the rear gate until 02:00."),
    notified="Fire Department (911), Property Management",
    subject="Fire department believes the fire started at an encampment in the brush strip. Individual seen leaving the area.",
    internal="Patrol officer was on meal break 23:30-00:00; second check of rear gate was 23:12.")
dispatch_tasks.append({"id": did, "account": 103, "location": loc_by_name[(103, "Rear Gate")], "locationType": "SITE_LOCATION",
                       "priority": "URGENT", "status": "CLOSED", "startedOn": iso(fire_at), "startDateTime": iso(fire_at),
                       "closedOn": iso(fire_at + timedelta(hours=2, minutes=12)),
                       "taskInstructions": "Fire at rear perimeter - respond, call 911, keep area clear", "report": fire_report})
# plus one still-open dispatch for the briefing
did += 1
open_at = at(NOW, 5, 40)
dispatch_tasks.append({"id": did, "account": 102, "location": loc_by_name[(102, "Main Gate")], "locationType": "SITE_LOCATION",
                       "priority": "HIGH", "status": "IN_PROGRESS", "startedOn": iso(open_at), "startDateTime": iso(open_at),
                       "closedOn": None, "taskInstructions": "Truck driver refusing to leave the gate lane", "report": None})
# routine daily activity reports last night (no flag)
for acc in (101, 102, 103):
    add_report(acc, None, None, at(NOW, 5, 30), summary="Routine patrols completed. No issues.")

# ---------------------------------------------------------------- site content
post_orders = [
    {"id": 601, "account": 103, "status": "ACTIVE", "version": 3, "subject": {"name": "Perimeter Patrol"},
     "details": "Check rear gate, fence line and loading area every 2 hours overnight. Report open gates or fence damage."},
    {"id": 602, "account": 103, "status": "ACTIVE", "version": 1, "subject": {"name": "Fire / Life Safety"},
     "details": "Call 911 first. Notify account manager and property management. Keep people clear; meet responders."},
    {"id": 603, "account": 102, "status": "ACTIVE", "version": 2, "subject": {"name": "Interior Patrol"},
     "details": "Walk all stairwells and the trailer yard once per hour overnight."},
    {"id": 604, "account": 101, "status": "ACTIVE", "version": 5, "subject": {"name": "Supervisor Duties"},
     "details": "Supervisors must not take meal breaks at the same time. One supervisor on post at all times."},
]

files = {
    "accounts": accounts, "site-locations": site_locations, "positions": positions, "employees": employees,
    "shifts": shifts, "work-sessions": work_sessions, "break-sessions": break_sessions,
    "dispatch-tasks": dispatch_tasks, "reports": reports, "report-fields": report_fields,
    "report-flags": report_flags, "report-templates": report_templates, "post-orders": post_orders,
}
for name, rows in files.items():
    (OUT / f"{name}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
(OUT / "_meta.json").write_text(json.dumps({"now": NOW.isoformat(), "note": "Synthetic data. All names fictional."}, indent=1))
print({k: len(v) for k, v in files.items()})
