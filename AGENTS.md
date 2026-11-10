# Instructions for AI agents working in this repo

This repo contains skills for analysing TrackTik data. Each skill is a folder under `skills/` with a `SKILL.md`
that explains when to use it, the script to run, and how to write up the results.

1. Before any TrackTik work, read `skills/tracktik-api-setup/SKILL.md` and `skills/tracktik-api-setup/references/api-gotchas.md`.
2. Match the user's request to a skill by its `description`, read that skill's `SKILL.md` in full, and follow it.
3. Everything is read-only. Never write to TrackTik, and never send email or messages on the user's behalf.
4. If `.env` is missing, use the synthetic data: set `TT_FIXTURES=fixtures`.
5. Respect each skill's tier (see `AUTONOMY-TIERS.md`). Tier 3 output is a draft for a person to review.
