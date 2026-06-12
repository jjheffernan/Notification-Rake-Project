#!/usr/bin/env bash
# Install agent skills: clone vendors, centralize in .agent/, symlink to agent folders.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
AGENT="$ROOT/.agent"
VENDOR="$AGENT/vendor"

relpath() {
  python3 -c "import os.path, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$1" "$2"
}

clone_or_update() {
  local url="$1" dest="$2"
  if [[ -d "$dest/.git" ]]; then
    echo "  update $dest"
    git -C "$dest" pull --ff-only
  else
    echo "  clone $url -> $dest"
    git clone --depth 1 "$url" "$dest"
  fi
}

echo "==> vendor repos"
mkdir -p "$VENDOR"
clone_or_update "https://github.com/JuliusBrussee/caveman" "$VENDOR/caveman"
clone_or_update "https://github.com/DietrichGebert/ponytail" "$VENDOR/ponytail"

echo "==> canonical skills in .agent/skills/ (relative symlinks)"
mkdir -p "$AGENT/skills"
link_skill() {
  local name="$1" src="$2"
  local rel
  rel="$(relpath "$src" "$AGENT/skills")"
  ln -sfn "$rel" "$AGENT/skills/$name"
}

for d in "$VENDOR/caveman/skills"/*/ "$VENDOR/ponytail/skills"/*/; do
  [[ -d "$d" ]] || continue
  link_skill "$(basename "$d")" "$d"
done

echo "==> canonical rules in .agent/rules/"
mkdir -p "$AGENT/rules"

CAVE_RULE="$AGENT/rules/caveman.mdc"
cat > "$CAVE_RULE" <<'EOF'
---
description: "Caveman mode — terse communication, ~75% fewer tokens, full technical accuracy"
alwaysApply: false
---

EOF
cat "$VENDOR/caveman/src/rules/caveman-activate.md" >> "$CAVE_RULE"

# Copy (not symlink) ponytail rules so they survive without vendor in git
cp -f "$VENDOR/ponytail/.cursor/rules/ponytail.mdc" "$AGENT/rules/ponytail.mdc"
cp -f "$VENDOR/ponytail/.windsurf/rules/ponytail.md" "$AGENT/rules/ponytail-windsurf.md"
cp -f "$VENDOR/ponytail/.clinerules/ponytail.md" "$AGENT/rules/ponytail-cline.md"
cp -f "$VENDOR/ponytail/AGENTS.md" "$AGENT/rules/ponytail-AGENTS.md"

link_into() {
  local target_dir="$1"
  mkdir -p "$target_dir"
  for skill in "$AGENT/skills"/*/; do
    [[ -L "$skill" || -d "$skill" ]] || continue
    name="$(basename "$skill")"
    rel="$(relpath "$skill" "$target_dir")"
    ln -sfn "$rel" "$target_dir/$name"
  done
}

link_rule() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  rel="$(relpath "$src" "$(dirname "$dest")")"
  ln -sfn "$rel" "$dest"
}

echo "==> Cursor (.cursor/skills + .cursor/rules)"
link_into "$ROOT/.cursor/skills"
link_rule "$AGENT/rules/caveman.mdc" "$ROOT/.cursor/rules/caveman.mdc"
link_rule "$AGENT/rules/ponytail.mdc" "$ROOT/.cursor/rules/ponytail.mdc"

echo "==> Windsurf"
link_rule "$AGENT/rules/caveman.mdc" "$ROOT/.windsurf/rules/caveman.md"
link_rule "$AGENT/rules/ponytail-windsurf.md" "$ROOT/.windsurf/rules/ponytail.md"

echo "==> Cline"
link_rule "$AGENT/rules/caveman.mdc" "$ROOT/.clinerules/caveman.md"
link_rule "$AGENT/rules/ponytail-cline.md" "$ROOT/.clinerules/ponytail.md"

echo "==> GitHub Copilot"
mkdir -p "$ROOT/.github"
cp -f "$AGENT/rules/ponytail-AGENTS.md" "$ROOT/.github/copilot-instructions.md"
cat >> "$ROOT/.github/copilot-instructions.md" <<'EOF'

# Notification Rake

See AGENTS.md, docs/functions.md, specs.md. Agent rules: .cursor/rules/
EOF

echo "==> AGENTS.md (project root)"
cat > "$ROOT/AGENTS.md" <<'EOF'
# Notification Rake — Agent Instructions

Vehicle listing platform. Read `specs.md` + `docs/functions.md` before editing Python.

## Skills (invoke in Cursor)

- `/caveman` — terse replies
- `/ponytail` — minimal code
- Sub-skills in `.agent/skills/` — run `make install-skills` after clone

Full ponytail/caveman rules live in `.agent/rules/` and `.cursor/rules/` — not duplicated here.
EOF

echo "==> done"
echo "Skills: $(find "$AGENT/skills" -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ') linked"
echo "Run: make install-skills  (or re-run this script after vendor updates)"
