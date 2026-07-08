# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

**Note:** `wontfix` already exists as a GitHub default label. Create the other four in the repo settings before running `/triage` at scale:

```bash
gh label create needs-triage --color BFD4F2 --description "Maintainer needs to evaluate"
gh label create needs-info --color FEF2C0 --description "Waiting on reporter"
gh label create ready-for-agent --color C2E0C6 --description "Fully specified, AFK-ready"
gh label create ready-for-human --color FBCA04 --description "Requires human implementation"
```
