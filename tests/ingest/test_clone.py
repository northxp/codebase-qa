import json
import subprocess
from pathlib import Path

import pytest

from app.ingest.clone import CloneError, _resolve_sha, clone_repo


def _cp(cmd, *, stdout="", stderr="", rc=0):
    return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)


FULL = "abc" + "0" * 37  # 40 chars


def test_resolve_sha_passthrough_for_full_sha():
    assert _resolve_sha("https://github.com/o/r", FULL) == FULL


def test_resolve_sha_expands_short_sha(monkeypatch):
    payload = json.dumps({"sha": "a" * 40}).encode()

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload

    monkeypatch.setattr(
        "app.ingest.clone.urllib.request.urlopen",
        lambda req, timeout: FakeResp(),
    )
    assert _resolve_sha("https://github.com/o/r", "abc") == "a" * 40


def test_resolve_sha_rejects_non_github_url():
    with pytest.raises(CloneError, match="not a GitHub repo"):
        _resolve_sha("https://gitlab.com/o/r", "abc")


def test_clone_runs_expected_git_commands(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _cp(cmd, stdout=FULL)
        return _cp(cmd)

    monkeypatch.setattr("app.ingest.clone.subprocess.run", fake_run)

    dest, sha = clone_repo("https://github.com/o/r", FULL, tmp_path / "r")
    assert sha == FULL
    assert ["git", "init", "-q"] in calls
    assert ["git", "remote", "add", "origin", "https://github.com/o/r"] in calls
    assert ["git", "fetch", "--depth", "1", "origin", FULL] in calls
    assert ["git", "checkout", "-q", "FETCH_HEAD"] in calls


def test_clone_raises_on_sha_mismatch(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _cp(cmd, stdout="bad" + "0" * 37)
        return _cp(cmd)

    monkeypatch.setattr("app.ingest.clone.subprocess.run", fake_run)

    with pytest.raises(CloneError, match="does not match"):
        clone_repo("https://github.com/o/r", FULL, tmp_path / "r")


def test_clone_raises_on_failed_git_command(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        return _cp(cmd, rc=128, stderr="fatal: not found")

    monkeypatch.setattr("app.ingest.clone.subprocess.run", fake_run)

    with pytest.raises(CloneError, match="failed"):
        clone_repo("https://github.com/o/r", FULL, tmp_path / "r")


def test_clone_is_idempotent(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    (repo / ".git").mkdir(parents=True)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "rev-parse", "--verify", "HEAD"]:
            return _cp(cmd, stdout=FULL)
        return _cp(cmd)

    monkeypatch.setattr("app.ingest.clone.subprocess.run", fake_run)

    dest, sha = clone_repo("https://github.com/o/r", FULL, repo)
    assert sha == FULL
    assert calls == [["git", "rev-parse", "--verify", "HEAD"]]


def test_clone_raises_on_unborn_head(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    (repo / ".git").mkdir(parents=True)

    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "--verify", "HEAD"]:
            return _cp(cmd, rc=128, stderr="fatal: Needed a single revision\n")
        return _cp(cmd)

    monkeypatch.setattr("app.ingest.clone.subprocess.run", fake_run)

    with pytest.raises(CloneError, match="unborn"):
        clone_repo("https://github.com/o/r", FULL, repo)
