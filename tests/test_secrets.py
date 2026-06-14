"""Guardrails: no secrets in tracked files or git index."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Likely real credentials — not dev placeholders documented in .env.example
SECRET_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),
]

PLACEHOLDER = re.compile(
    r"change-me|example|placeholder|test-token|test-key|your-",
    re.IGNORECASE,
)

FORBIDDEN_TRACKED = {".env"}
FORBIDDEN_TRACKED_PREFIXES = (".env.",)


def _git_ls_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def test_env_file_not_tracked():
    tracked = _git_ls_files()
    for path in tracked:
        assert path not in FORBIDDEN_TRACKED, f"{path} must not be committed"
        if path.startswith(FORBIDDEN_TRACKED_PREFIXES) and path != ".env.example":
            raise AssertionError(f"{path} must not be committed (use .env.example)")


def test_tracked_files_have_no_secret_patterns():
    findings: list[str] = []
    for rel in _git_ls_files():
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                snippet = match.group(0)
                if PLACEHOLDER.search(snippet):
                    continue
                findings.append(f"{rel}: {pattern.pattern}")
    assert not findings, "possible secrets in tracked files:\n" + "\n".join(findings)
