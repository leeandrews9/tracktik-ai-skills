---
name: tracktik-api-setup
description: Connect an AI coding agent to a TrackTik tenant through the REST API, safely and read-only. Covers creating a least-privilege API user, the .env file, testing the connection, paging, and the API quirks that silently return wrong answers (ISO date filters ignored, hours missing unless requested, inactive records hidden, reports needing a date filter). Use this first whenever someone wants to pull anything from TrackTik, says "connect to TrackTik", "use the TrackTik API", gets suspicious results from a TrackTik query, or before running any other skill in this repo.
---

# TrackTik API setup (read-only)

Every other skill in this repo builds on this one. It holds the shared client
(`scripts/tracktik_client.py`) and the API behaviour that took the most time to learn.

## 1. Before you connect: scope the access

Handing an AI agent full admin access to your tenant is a real risk. Do this first:

1. In TrackTik, create a **dedicated API user** (for example `api-ai-readonly`). Don't reuse a person's login.
2. Give it a security role with **read permissions only** for the modules the skills need: accounts/sites,
   positions, employees, shifts, work and break sessions, reports, dispatch tasks, site locations, post orders.
3. Ask Trackforce support for your tenant URL and, if your tenant uses them, an OAuth client id and secret.
4. Keep the credentials in a `.env` file that is never committed (the repo's `.gitignore` already covers it).

The client in this repo only implements HTTP GET. There's no code path that writes to your tenant.

## 2. Configure

Copy `.env.example` to `.env` at the repo root and fill it in:

```
TT_BASE_URL=https://yourcompany.staffr.net
TT_USERNAME=api-ai-readonly
TT_PASSWORD=...
TT_CLIENT_ID=          # only if your tenant issued one
TT_CLIENT_SECRET=
TT_TZ=America/Los_Angeles
```

Test it:

```
pip install -r requirements.txt
python skills/tracktik-api-setup/scripts/tracktik_client.py
```

You should see `AUTH OK` and counts of accounts and employees.

**No tenant handy?** Set `TT_FIXTURES=fixtures` instead. Every skill then runs against the synthetic
dataset in `fixtures/` (fictional sites, people and incidents), which is good for demos and for trying the
skills before you point them at production.

## 3. Using the client in a new script

```python
import sys; from pathlib import Path
sys.path.insert(0, str(Path("skills/tracktik-api-setup/scripts").resolve()))
from tracktik_client import TrackTik, epoch, local, ref_id

tt = TrackTik()
shifts = tt.all("/shifts", {
    "startsOn:gte": epoch("2026-10-01"), "startsOn:lte": epoch("2026-10-31", end_of_day=True),
    "include": "position,employee",
    "fields": "id,position,employee,startDateTime,endDateTime,clockedHours,approvedHours,billableHours",
})
```

- `tt.all(path, params)` pages through everything (100 rows per page) until `meta.count`.
- `tt.count(path, params)` costs one request; use it to size a pull before running it.
- `tt.check_filter(path, params)` warns if TrackTik silently ignored your filter.
- The client throttles to about 4 requests per second and retries 429 and 5xx errors.

## 4. Quirks that silently give wrong answers

Read `references/api-gotchas.md` before writing any new query. The short version:

1. **Date filters only work as epoch seconds.** ISO strings like `2026-10-01` are ignored without any error,
   and you get the whole tenant back. Always use `epoch()`.
2. **Sanity-check every filtered pull:** if the filtered count equals the unfiltered count, your filter was dropped.
3. **Hours are null unless you name them in `fields=`.**
4. **Inactive employees and closed sites are hidden** unless you pass `includeInactive=true`.
5. **`/reports` refuses to run without a date filter**, and only `submittedOn` works for it.
6. **Report fields can be confidential or admin-only.** Check `templateField.confidential` and `adminOnly`
   before anything goes to a client.

`references/endpoints.md` lists the endpoints these skills use and the fields worth asking for.

## 5. Delivering results

- Say how many rows you pulled against `meta.count`, and say plainly if anything is incomplete.
- Keep the scripts you wrote next to the output so the pull can be re-run.
- Treat officer names and phone numbers as personal data. Don't paste them anywhere public.
