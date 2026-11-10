# Autonomy tiers: how much should an agent do on its own?

Every agent I've run in a guard company runs at a set level of autonomy. The tier depends on the **risk of the
action**, not on how smart the model is. Decide the tier before you build the agent.

| Tier | The agent... | A person... | Good for |
|---|---|---|---|
| **1: Auto-execute** | reads, analyses and posts results | reads the output | Routine, low-risk, internal work |
| **2: Propose and approve** | prepares the action and asks | approves, rejects or adjusts with one click, then the agent acts | Operational actions that are reversible |
| **3: Draft only** | drafts | edits, finalises and sends it themselves | Anything client-facing, or with legal or contractual consequences |

## Examples

**Tier 1: auto-execute**
- Daily ops briefing posted to the ops channel at 06:30
- Weekly client health reports, with security gaps and upsell opportunities
- Weekly sales pipeline report
- Briefs before external meetings

**Tier 2: propose and approve**
- Outreach to officers (open-shift offers, reminders): the agent posts a card in the ops channel with
  **Approve / Reject / Adjust** buttons, and only sends after approval
- Suggested schedule fills for a call-off

**Tier 3: draft only**
- Client follow-ups after an incident
- Quotes and anything with pricing
- Post orders (contracts have to reflect post orders, and some insurers get nervous about AI touching them)
- Hiring recommendations and job postings

## Moving an agent up a tier

Start lower than you think, then earn the promotion:

1. **Shadow mode.** The agent decides but doesn't act. Log its picks next to what your people actually did.
2. **Measure the match rate.** How often did it pick what your scheduler or ops lead picked? Where it differed,
   who was right?
3. **Promote when the numbers clear your bar**, for example from draft to approve once it matches 90% of the
   time for a month. Keep a one-switch way to drop it back down.

## Guardrails that apply at every tier

- A dedicated API user with the narrowest permissions the agent needs. Read-only until it truly needs to write.
- A record of every action: what it saw, what it decided, who approved it.
- Confidential fields stay internal. The agent can read them; it never sends them out.
- A human owner for every agent. If nobody owns it, turn it off.

All the skills in this repo are **Tier 1** (read and analyse) or **Tier 3** (draft). Moving to Tier 2, where agents
write back to TrackTik or message people with approval, is where the bigger wins are. It's also where the
engineering (approvals, audit trail, rollback, monitoring) matters most.
