# Notification Rake — Agent Instructions

Vehicle listing platform. Read `specs.md` + `docs/functions.md` before editing Python.

## Skills (invoke in Cursor)

- `/caveman` — terse replies
- `/ponytail` — minimal code
- `/grill-me` — relentless plan/design interview ([mattpocock/skills](https://github.com/mattpocock/skills))
- `/grill-with-docs`, `/tdd`, `/to-prd`, `/to-issues`, `/triage`, … — same vendor set
- Sub-skills in `.agent/skills/` — run `make install-skills` after clone

Full ponytail/caveman rules live in `.agent/rules/` and `.cursor/rules/` — not duplicated here.

## Agent skills

### Issue tracker

GitHub Issues on `jjheffernan/Notification-Rake-Project` via `gh` CLI; external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — `CONTEXT.md` + `docs/adr/` at repo root (lazy-created). See `docs/agents/domain.md`.
