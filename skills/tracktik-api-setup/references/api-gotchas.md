# TrackTik REST API: gotchas found the hard way

These were all found on a production tenant. Your tenant's configuration may differ, so verify with
`tt.count()` before you trust a filter.

## Filters

| Behaviour | What to do |
|---|---|
| Date filters with ISO strings (`startsOn:gte=2026-10-01`, with or without a time zone offset) are **silently ignored**. You get the whole collection back. | Use epoch seconds: `startsOn:gte=1790000000`. The client's `epoch()` helper does this. |
| Some date filters are ignored in every form: `reports?reportDateTime:gte`, `/shift-logs?createdOn:gte`, `/dispatch-tasks?createdOn:gte`. | `reports` → filter on `submittedOn`. `dispatch-tasks` → filter on `startedOn`. Re-check dates client-side. |
| Epoch filters that **do** work: `shifts.startsOn`, `work-sessions.startedOn`, `break-sessions.startedOn`, `dispatch-tasks.startedOn`, `reports.submittedOn`, `checkpoint-tour-sessions.startedOn`, `checkpoint-scans.scannedOn`, `shifts.modifiedOn`. | |
| `/reports` returns **400 "Missing required filters"** without a date filter. | Always pass `submittedOn:gte` (and usually `:lte`). |
| `/mobile-device-geo-locations` also requires a `createdOn` filter. | |
| `/user-login-logs` ignores every filter. | `sort=-loggedInOn` and stop paging once you're past your window. |
| `reports?scope=HAS_INCIDENT` works and is the cleanest "incident reports only" filter. | |

**Rule of thumb:** after any filtered pull, compare `tt.count(path, filters)` with `tt.count(path, {})`. If they
match on a large collection, the filter was dropped.

## Fields and includes

- **Hours come back null unless named in `fields=`**: `clockedHours, approvedHours, billableHours, payableHours,
  overtimeHours, holidayHours, plannedDurationHours`.
- `/shifts` has no `account` field or include. Use `include=position` and read `position.account`.
  Asking for `fields=account` returns 400.
- `/reports` doesn't accept `fields=`. Use `include=reportFields` or query `/report-fields?report=<id>&include=templateField`.
- Report field values come back as `{"value": ...}`. The label is on `templateField.label`.
- `templateField.confidential` and `templateField.adminOnly` mark fields that must not leave your company.
- **`account` vs `siteLocation` on reports:** `account` is the site the report was filed from, and it's always set.
  `siteLocation` is an optional named spot *inside* that site (`/site-locations`: a stairwell, gate or dock), and it
  only exists where an admin has set Site Locations up for that site. A null `siteLocation` doesn't mean the report
  has no location.
- A dispatch task's `location` is often just the account address (`locationType=ACCOUNT_ADDRESS`). If there's a
  spot inside the site, it's on the linked report's `siteLocation`.
- Relations come back as plain ids, or as objects when you `include=` them. The client's `ref_id()` handles both.

## Hidden records

- `/employees` and `/accounts` default to **active only**. Pass `includeInactive=true` for terminated
  employees and closed sites. This matters for anything historical: billing disputes, audits, claims.
- Your tenant probably has a test or sandbox site and a few service accounts (API users, BI users). Find their ids
  once and exclude them from operational metrics.

## Audit trail

- `/audit-logs` exists, but the API user usually gets **403** unless its role has the audit-log permission.
- Shifts carry `createdBy`, `publishedBy` and `updatedBy`, but **no timestamps** for those events.
- To estimate when a bulk schedule change happened, sample `tt.count("/shifts", {"modifiedOn:lte": <epoch>})`
  on an hourly grid. The hour where the count jumps is your answer (one request per point).

## Data quality checks worth running

- Unlinked work sessions (no `shift`) are often ghost or duplicate punches.
- `attendanceStatus = MISSED` can show up on salaried staff who never punch, even though they worked.
- Look for plain-text alarm codes and door codes in post orders and site notes.
