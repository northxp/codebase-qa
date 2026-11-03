"""Clone a public GitHub repo at a pinned commit SHA.

Uses a shallow fetch of the exact SHA instead of a full clone — the full
history of a repo like psf/requests is ~50MB and thousands of commits;
the tree at one SHA is ~1MB and that is all we need.

GitHub's upload-pack only accepts full 40-character SHAs (or branch/tag
refs) for fetch. Abbreviated SHAs are resolved to full SHAs via the
GitHub REST API before fetching.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path

_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_GITHUB_URL_RE = re.compile(r"github\.com[/:]([^/]+)/([^/.]+?)(?:\.git)?/?$")


class CloneError(RuntimeError):
    """Raised when cloning or SHA verification fails."""


def _resolve_sha(url: str, sha: str, *, timeout: int = 10) -> str:
    """Return the full 40-char SHA. Expand a short SHA via the GitHub API."""
    s = sha.strip().lower()
    if _FULL_SHA_RE.fullmatch(s):
        return s

    m = _GITHUB_URL_RE.search(url)
    if not m:
        raise CloneError(
            f"cannot resolve short SHA {sha!r}: URL {url!r} is not a GitHub repo"
        )
    owner, repo = m.group(1), m.group(2)
    api = f"https://api.github.com/repos/{owner}/{repo}/commits/{s}"
    req = urllib.request.Request(
        api,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "codebase-qa",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise CloneError(
            f"failed to resolve short SHA {sha!r} via {api}: {e}"
        ) from e

    full = data.get("sha", "")
    if not _FULL_SHA_RE.fullmatch(full):
        raise CloneError(f"GitHub API returned an invalid SHA {full!r}")
    return full


def clone_repo(
    url: str,
    sha: str,
    dest: Path,
    *,
    timeout: int = 120,
) -> tuple[Path, str]:
    """Clone `url` at `sha` into `dest`. Returns (dest, full_sha).

    Idempotent: if `dest` already has a `.git/` whose HEAD matches `sha`,
    returns immediately without re-cloning. If `dest` exists with a
    different HEAD, or with an unborn HEAD (partial previous clone), raises
    CloneError with a specific, actionable message.
    """
    full_sha = _resolve_sha(url, sha)
    dest = dest.resolve()

    if (dest / ".git").is_dir():
        # `--verify` forces git to actually resolve HEAD to a commit. Without
        # it, `git rev-parse HEAD` on an unborn repo (init ran, no commits)
        # just echoes the literal string "HEAD" instead of failing.
        existing = _run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=dest, check=False
        )
        if existing.returncode != 0:
            raise CloneError(
                f"{dest} has a .git/ but HEAD is unborn (partial clone from "
                f"a previous run). Delete the directory and retry:\n"
                f"  rm -rf {dest}"
            )
        head = existing.stdout.strip()
        if not head.startswith(full_sha):
            raise CloneError(
                f"{dest} already exists at a different commit "
                f"({head[:12]}); refusing to overwrite"
            )
        return dest, head

    dest.mkdir(parents=True, exist_ok=True)

    # `git clone --branch <sha>` fails because a SHA is not a branch or tag.
    # The correct pattern is: init → remote add → shallow fetch of the full
    # SHA → checkout FETCH_HEAD.
    _run(["git", "init", "-q"], cwd=dest, timeout=timeout)
    _run(["git", "remote", "add", "origin", url], cwd=dest, timeout=timeout)
    _run(
        ["git", "fetch", "--depth", "1", "origin", full_sha],
        cwd=dest,
        timeout=timeout,
    )
    _run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=dest, timeout=timeout)

    head = _run(
        ["git", "rev-parse", "HEAD"], cwd=dest, timeout=timeout
    ).stdout.strip()
    if not head.startswith(full_sha):
        raise CloneError(
            f"HEAD {head[:12]} does not match requested SHA {full_sha[:12]}"
        )

    return dest, head


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int = 60,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise CloneError(
            f"{' '.join(cmd)} failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result
