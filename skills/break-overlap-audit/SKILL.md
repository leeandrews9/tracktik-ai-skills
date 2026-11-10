---
name: break-overlap-audit
description: Check TrackTik punch data for two roles at one site taking breaks at the same time, for example a supervisor and an assistant supervisor both at lunch. Counts every overlap over a period, checks how many other officers were on post during each one, and prices the overlapped time as a client credit. Use this whenever a client or manager says staff are taking lunches or breaks together, asks whether coverage lapsed, asks "how often has this happened", wants a credit or concession calculated for overlapping breaks, or wants to verify a break policy is being followed at a site.
---

# Break overlap audit

**The story behind this skill:** a client noticed that the supervisor and assistant supervisor at their site had
started taking lunch at the same time, which was against policy. Within two hours of that email we knew how many
times it had happened in the last 90 days, that at least three other officers were on site every time (so there was
no lapse in coverage), and what the overlapped time cost at the assistant supervisor's rate. That amount went on the
next invoice as a credit. The client was impressed enough to introduce us to a new prospect.

This skill reproduces that analysis. It is **Tier 1** (read-only analysis). Any credit you decide to issue is a
person's decision.

## Inputs to confirm

| Input | Example | Notes |
|---|---|---|
| Site | `--account 101` | Find the id with `GET /accounts?includeInactive=true` and match on name |
| Role A, Role B | `"Site Supervisor"`, `"Assistant Supervisor"` | Exact TrackTik **position names**, comma-separate to combine several |
| Period | `--days 90` | Match what the client asked about |
| Break type | `MEAL` (default), `REST`, `ALL` | Lunch complaints = `MEAL` |
| Rate | `--rate 38.50` | Usually the **bill rate of the lower-paid role** (the client paid for that person to be on post). Ask, don't guess |
| Minimum coverage | `--min-coverage 2` | Officers who must remain on post. Check the site's post orders |

If you don't know the position names, run the script with a guess and it prints the names that exist at the site.

## Run it

```
python skills/break-overlap-audit/scripts/break_overlap.py --account 101 \
  --role-a "Site Supervisor" --role-b "Assistant Supervisor" \
  --days 90 --rate 38.50 --min-coverage 2 --out out/break-overlap
```

Output: `overlaps.csv` (one row per overlap: date, times, minutes, who else was on post) and `summary.json`
(totals, credit, coverage check).

Demo without a tenant: `TT_FIXTURES=fixtures` with the command above (Harbor Point has this exact pattern).

## How it works

1. Pulls actual punches (`/work-sessions`) and breaks (`/break-sessions`) for the period, using epoch filters.
2. Maps each break → work session → position name.
3. For every pair of role A and role B breaks that intersect, takes the overlapping minutes.
4. Counts other officers who were clocked in for the **whole** overlap and **not** on their own break.
5. Prices the overlap at `--rate`.

## Writing it up

Give the client a short, factual answer. Template:

> We reviewed every meal break taken by the [Role A] and [Role B] at [Site] from [start] to [end] using our
> TrackTik timekeeping records. Their breaks overlapped on **[N] days**, for **[H] hours** in total. During every
> overlap at least **[min]** other officers were on post, so the site was never without coverage. Because the
> overlap is against our post orders, we're crediting **$[credit]** ([H] hours at the [Role B] rate) on your next
> invoice. We've reminded both supervisors of the policy and will keep monitoring it.

Before sending, check:
- Any day with `coverage_ok = false`. If coverage did lapse, that's an escalation, not a footnote. Tell the person
  you're working with first.
- Breaks still open (`open_breaks_excluded`). An unclosed break can mean a missed punch, not a long lunch.
- First overlap date. It often lines up with a schedule change or a new hire, which is useful context.

## Limits

- It uses punch data. If officers don't punch breaks in TrackTik, the answer is "we can't tell from the
  system". Say so; don't guess.
- It isn't legal advice on meal-and-rest-break compliance. It answers an operational and billing question.
