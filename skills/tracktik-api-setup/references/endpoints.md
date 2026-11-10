# Endpoints used by these skills

All paths are under `<TT_BASE_URL>/rest/v1`. Pagination: `limit` (max 100) + `offset`; `meta.count` is the total.

| Endpoint | Used for | Useful params / fields |
|---|---|---|
| `/accounts` | Sites and clients | `includeInactive=true`, `include=address,parentAccount`. `type`: MULTI = client, SITE = site |
| `/site-locations` | Named spots inside a site (stairwell, gate, dock) | `account`, `name`, `parent` |
| `/positions` | Posts and roles; position → account | `account=<id>`, `includeInactive=true` |
| `/employees` | Officers | `includeInactive=true` |
| `/shifts` | Schedule | `startsOn:gte/lte` (epoch), `include=position,employee`, `fields=` (hours: see gotchas), `vacant`, `attendanceStatus` |
| `/work-sessions` | Actual punches | `startedOn:gte/lte` (epoch), `account`, `position`, `employee`, `shift` |
| `/break-sessions` | Meal and rest breaks | `startedOn:gte/lte` (epoch), `type` (MEAL / REST / BREAK), `workSession`, `employee` |
| `/dispatch-tasks` | Dispatches | `startedOn:gte/lte` (epoch), `priority`, `status`, `closedOn`, `report`, `location` / `locationType` |
| `/reports` | Reports, incidents | **Requires** `submittedOn:gte/lte`. `scope=HAS_INCIDENT`. Fields: `reportFlag`, `siteLocation`, `dispatchTask`, `reportTemplate` |
| `/report-fields` | Report content | `report=<id>`, `include=templateField` (label, confidential, adminOnly) |
| `/report-flags` | Incident types | `name` |
| `/report-templates` | Report types | `name` |
| `/post-orders` | Site instructions | `account`, `include=subject` (and `attachment` for files) |
| `/checkpoint-tour-sessions`, `/checkpoint-scans` | Guard tours | `startedOn` / `scannedOn` (epoch) |
| `/contracts`, `/invoices`, `/invoice-lines` | Billing | `/invoice-lines?invoice=<id>` |

Ask Trackforce support for the REST API documentation for your tenant, and point your AI tool at it. It's
thorough. API error responses also include a `documentationLink` for the specific error.
