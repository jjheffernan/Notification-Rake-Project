# Documentation

Two parallel doc sets — same content, different targets:

| Location | Use |
|----------|-----|
| [`wiki/`](wiki/Home.md) | **GitHub Wiki** — copy to `<repo>.wiki.git` |
| This folder | **Repo docs** — linked from README |

## GitHub Wiki sync

1. Enable Wiki on the GitHub repository (Settings → Features).
2. Clone the wiki repository:
   ```bash
   git clone https://github.com/<owner>/<repo>.wiki.git
   ```
3. Copy wiki pages:
   ```bash
   cp docs/wiki/*.md /path/to/<repo>.wiki/
   ```
4. Commit and push the wiki repo.

Wiki conventions used in `docs/wiki/`:

- **Home.md** — landing page (GitHub Wiki default)
- **_Sidebar.md** — left navigation
- Cross-links: `[Architecture](Architecture)` — no `.md` extension
- Flat filenames with hyphens: `Setup-and-Quick-Start.md`

Do not use `../specs.md` style links inside wiki pages — use wiki page names or full GitHub blob URLs for repo-only files.

## Repo docs (mirror)

| File | Wiki equivalent |
|------|-----------------|
| [architecture.md](architecture.md) | [Architecture](wiki/Architecture.md) |
| [functions.md](functions.md) | [Development](wiki/Development.md) + [API-Reference](wiki/API-Reference.md) |
| [deploy.md](deploy.md) | [Deployment](wiki/Deployment.md) |
| [yahoo-setup.md](yahoo-setup.md) | [Yahoo-Auctions-JP](wiki/Yahoo-Auctions-JP.md) |
| [plans/yahoo-proxy-ingestion.md](plans/yahoo-proxy-ingestion.md) | Detailed Yahoo roadmap |
| [audit.md](audit.md) | Historical audit notes |

Product vision: [specs.md](../specs.md) (repo root).
