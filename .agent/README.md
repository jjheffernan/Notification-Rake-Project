# Agent skills hub

Central store for AI agent skills. Agent-specific folders symlink here — one source of truth, no duplication.

## Layout

```text
.agent/
├── vendor/          # upstream repos (caveman, ponytail, mattpocock-skills)
├── skills/          # symlinks → vendor/*/skills/*
├── rules/           # canonical rule files per agent
└── scripts/
    └── install.sh   # clone vendors + wire symlinks
```

## Installed skills

| Skill | Source | Trigger |
|-------|--------|---------|
| `caveman` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | `/caveman [lite\|full\|ultra]` |
| `caveman-commit`, `-review`, `-stats`, `-compress`, `cavecrew` | caveman | `/caveman-*` |
| `ponytail` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | `/ponytail [lite\|full\|ultra]` |
| `ponytail-review`, `-audit`, `-debt`, `-gain`, `-help` | ponytail | `/ponytail-*` |
| `grill-me`, `grilling` | [mattpocock/skills](https://github.com/mattpocock/skills) | `/grill-me` |
| `grill-with-docs`, `tdd`, `to-prd`, `to-issues`, `triage`, … | mattpocock | engineering + productivity buckets |

## Agent symlinks

| Agent | Skills | Rules |
|-------|--------|-------|
| Cursor | `.cursor/skills/*` → `.agent/skills/*` | `.cursor/rules/{caveman,ponytail}.mdc` |
| Windsurf | — | `.windsurf/rules/` |
| Cline | — | `.clinerules/` |
| Copilot | — | `.github/copilot-instructions.md` |

## Install / update

```bash
make install-skills
# or: .agent/scripts/install.sh
```

Re-run after pulling vendor updates or cloning fresh.

First-time Matt Pocock setup in a session: run `/setup-matt-pocock-skills` to configure issue tracker / triage labels / docs paths for that skill set.
