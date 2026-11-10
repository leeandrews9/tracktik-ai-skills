---
name: incident-followup-drafter
description: Draft the account manager's follow-up email to a client after a significant incident in TrackTik, covering what happened, what was done immediately, what is changing so it doesn't happen again, and an optional offer, for a person to review and send. Use this whenever someone asks to follow up with a client about an incident, write to the client about last night, draft an incident follow-up, tell the client what we're doing about something, or turn an incident report into a client email. Never sends anything itself.
---

# Incident follow-up drafter

TrackTik already sends the immediate alert when a priority incident happens. What clients remember is the
**follow-up**: the next-day note from their account manager saying what you did about it.

Example: a fire started in the brush outside a client's perimeter and burned through the rear gate. The client was
notified right away. The next day the account manager followed up: a new patrol checkpoint at the gate (tracked
in TrackTik), refresher fire-protocol training for the officers on that site, and an offer to quote a mobile
camera trailer for the fence line.

**Tier 3 (draft only).** This skill drafts. A person checks every fact and every commitment, then sends it.
Anything client-facing, or with legal or contractual consequences, stays Tier 3.

## Run it

```
python skills/incident-followup-drafter/scripts/fetch_incident.py --report <report id> --out out/incident
python skills/incident-followup-drafter/scripts/fetch_incident.py --account <site id> --latest
```

Demo: `TT_FIXTURES=fixtures` with `--account 103 --latest` (the Westgate fire).

`incident.json` contains the incident, the dispatch timeline, **client-safe** report fields, the site's other incidents
over the last 90 days, and the site's active post orders. Confidential and admin-only fields are moved to
`INTERNAL_ONLY_do_not_send`.

## Hard rules

1. **Never use anything from `INTERNAL_ONLY_do_not_send` in the email.** That includes subject descriptions,
   supervisor notes, and anything about officer performance. You may use it to warn the person reviewing the draft.
2. **Don't invent actions.** List the corrective steps as **proposals** in a separate note to the reviewer, marked
   `[CONFIRM]`, unless they're already recorded in TrackTik or the person told you they happened.
3. **No prices, no admissions of fault, no promises about outcomes.** If the incident could lead to a claim
   (injury, damage you might be blamed for), say so to the reviewer and suggest they check with their manager or
   insurer before sending.
4. One optional offer at most, and only if it clearly fits the incident: a camera, a patrol point or an added post.

## Draft structure

**Subject:** Follow-up: [incident type] at [site], [date]

1. **What happened**: 2-3 factual sentences from the client-safe summary. Times in local time.
2. **What we did right away**: from "Action Taken" and the dispatch timeline (called 911 at 23:49, notified you at 23:55...).
3. **What we're doing next**: 2-3 concrete steps, each something you can show later: a new checkpoint, updated
   post orders, refresher training, more patrols at that spot for N weeks.
4. **Optional**: one offer that matches the gap ("If you'd like more coverage on the fence line, we can quote a
   mobile camera trailer.").
5. **Close**: direct contact and an invitation to talk.

Then, **below the draft**, give the reviewer:
- `[CONFIRM]` items: every step that isn't yet a fact.
- Internal flags: anything from the internal-only fields worth knowing (for example, the officer was on break when
  the fire started). These are for the reviewer, never for the client.
- Pattern note: if `other_incidents_same_location` is greater than zero, mention it. It strengthens the case for
  the fix.

## Tone

Calm, specific, accountable. Short sentences. No jargon, no exclamation marks, nothing defensive. The client should
finish reading it thinking "they're on top of it".
