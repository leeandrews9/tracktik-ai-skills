# TrackTik AI Skills

**Ready-to-use AI skills for security companies running TrackTik.** Point Claude Code, Codex or a similar AI coding
tool at your TrackTik data and get answers in minutes: who took lunch at the same time, where your overnight calls
really come from, what happened last night across every site.

Shared from the Trackforce customer webinar *"Get answers. Take action. Stay in control with AI in TrackTik."*

> Everything here is **read-only**. No skill in this repo writes to your TrackTik tenant.

---

## The skills

| Skill | What it answers | Tier |
|---|---|---|
| [`tracktik-api-setup`](skills/tracktik-api-setup/SKILL.md) | Connects safely, plus the API quirks that silently return wrong answers. **Start here.** | – |
| [`break-overlap-audit`](skills/break-overlap-audit/SKILL.md) | "Are our supervisors taking lunch together? How often, was the site covered, and what do we credit the client?" | 1 |
| [`dispatch-hotspot-finder`](skills/dispatch-hotspot-finder/SKILL.md) | "Where do our overnight calls actually come from?" (one stairwell drove 36% at one property) | 1 |
| [`daily-ops-briefing`](skills/daily-ops-briefing/SKILL.md) | "What happened last night, and what needs action this morning?" | 1 |
| [`incident-followup-drafter`](skills/incident-followup-drafter/SKILL.md) | Drafts the account manager's next-day note to the client after an incident | 3 |
| [`site-risk-snapshot`](skills/site-risk-snapshot/SKILL.md) | One-page QBR snapshot: incident rate, trend, hotspots, indicator score | 1 / 3 |

**Tier 1** = the agent analyses on its own. **Tier 3** = it drafts and a person sends. See
[AUTONOMY-TIERS.md](AUTONOMY-TIERS.md) for the framework, including how to move an agent up a tier.

---

## Quick start (about 5 minutes)

```bash
git clone https://github.com/leeandrews9/tracktik-ai-skills.git
cd tracktik-ai-skills
pip install -r requirements.txt
```

**1. Try it without a tenant.** The repo includes a synthetic dataset (fictional sites, people and incidents):

```bash
export TT_FIXTURES=fixtures          # PowerShell: $env:TT_FIXTURES="fixtures"
python skills/dispatch-hotspot-finder/scripts/hotspots.py
python skills/break-overlap-audit/scripts/break_overlap.py --account 101 \
  --role-a "Site Supervisor" --role-b "Assistant Supervisor" --rate 38.50 --min-coverage 2
```

**2. Connect your tenant.** Read [`tracktik-api-setup`](skills/tracktik-api-setup/SKILL.md) first. Create a
read-only API user, then copy `.env.example` to `.env`, fill it in, and run:

```bash
python skills/tracktik-api-setup/scripts/tracktik_client.py    # should print AUTH OK
```

**3. Use it from your AI tool.**

- **Claude Code**: copy the skills where Claude Code finds them (`mkdir -p .claude && cp -r skills .claude/skills`),
  open Claude Code in this folder, and ask in plain English:
  *"Did the supervisor and assistant supervisor at Harbor Point take lunch at the same time in the last 90 days?"*
- **Codex and other agents**: `AGENTS.md` points them at the skills. Open the folder and ask the same question.

---

## Good questions to try

- "Which site had the most overnight dispatches last quarter, and where at the site?"
- "Give me the overnight briefing."
- "Draft a follow-up to the client about last night's fire at Westgate."
- "Build a QBR risk snapshot for Meridian Distribution Center."
- "How many times did our two supervisors' meal breaks overlap at Harbor Point, and what's the credit at $38.50 an hour?"

---

## Safety

- **Read-only by design.** The shared client only implements HTTP GET.
- **Least privilege.** Use a dedicated API user with read permissions only. Never a person's admin login.
- **Secrets stay local.** `.env` is git-ignored, and tokens are held in memory, never written to disk.
- **Confidential fields stay internal.** The incident drafter separates TrackTik fields marked confidential or
  admin-only and never puts them in a client draft.
- **Personal data.** Officer names and contact details come back from the API. Treat outputs accordingly.

---

## What's deliberately not here

These skills **read and draft**. The bigger wins come from agents that **act**, safely, with approvals:

- Closed CRM deal → contract parsed → site, rates, post orders, job posting and training built automatically
- Officer outreach and schedule fills approved with one click in Teams
- TrackTik → accounting billing sync running around the clock
- Always-on audits instead of on-request ones
- QBR risk scoring that adds crime, FEMA and FBI data to your TrackTik history

See [docs/whats-possible.md](docs/whats-possible.md) for how these fit together.

---

## About

Built by **Lee Andrews**, security operator and Trackforce Customer Advisory Board member. I've built AI agents on
top of TrackTik for daily operations, client reporting, incident follow-up and back-office work, using AI coding
tools on the TrackTik API without a development team.

**If you'd like to build agents like these for your company, or just compare notes, connect with me on
[LinkedIn](https://www.linkedin.com/in/leeandrews9/).**

---

<sub>Not affiliated with or endorsed by Trackforce. TrackTik is a trademark of its owner. Provided as-is under the MIT
License, with no warranty. Outputs are operational analysis, not legal, HR or insurance advice. Verify before acting.</sub>
