"""Filter a cloned repository to the Python source files we care about.

The PDF's definition: "Python files and lines (comments and blanks included)
outside tests, docs and examples folders." This module is that rule, in code.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

EXCLUDED_DIRS: frozenset[str] = frozenset({
    # version control / tooling
    ".git", ".github", ".gitlab", ".tox", ".venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__",
    # test directories (by name; a file called tests.py is still source)
    "tests", "test", "testing",
    # documentation
    "docs", "doc",
    # examples / samples
    "examples", "example", "samples",
    # benchmarks
    "benchmarks", "bench", "benchmark",
    # build artifacts / vendored
    "node_modules", "build", "dist",
})

MAX_FILE_BYTES = 1_000_000  # 1 MB — larger is generated, minified, or data


def iter_source_files(repo_root: Path) -> Iterable[Path]:
    """Yield .py files under repo_root, skipping excluded directories and huge files."""
    repo_root = repo_root.resolve()
    for path in repo_root.rglob("*.py"):
        rel = path.relative_to(repo_root)
        # Match on *directory components* only. `rel.parts[:-1]` is the parent
        # chain; the filename itself is `rel.parts[-1]` and is never matched
        # against EXCLUDED_DIRS — that's why `mytests.py` at the repo root is
        # included while `tests/anything.py` is not.
        if any(part in EXCLUDED_DIRS for part in rel.parts[:-1]):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path
