"""End-to-end ingest: clone → filter → chunk → embed → write, with per-stage timers."""
from __future__ import annotations

import time
from pathlib import Path

import psycopg
import tiktoken

from app.config import get_settings
from app.ingest.chunk import chunk_file
from app.ingest.clone import clone_repo
from app.ingest.embed import embed_texts
from app.ingest.filter import iter_source_files
from app.ingest.schema import apply_schema
from app.ingest.write import ensure_repo_and_commit, write_chunks


def run_ingest(
    url: str,
    sha: str,
    dest: Path,
    *,
    repo_name: str | None = None,
) -> dict:
    """Run the full ingest pipeline. Returns a summary dict with timings."""
    name = repo_name or url
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    t = time.perf_counter()
    root, full_sha = clone_repo(url, sha, dest)
    timings["clone"] = time.perf_counter() - t

    t = time.perf_counter()
    files = sorted(iter_source_files(root))
    timings["filter"] = time.perf_counter() - t

    t = time.perf_counter()
    enc = tiktoken.get_encoding("cl100k_base")
    all_chunks = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(f.relative_to(root))
        all_chunks.extend(
            chunk_file(text, path=rel, repo=name, commit_sha=full_sha)
        )
    timings["chunk"] = time.perf_counter() - t

    t = time.perf_counter()
    embeddings = embed_texts([c.text for c in all_chunks])
    timings["embed"] = time.perf_counter() - t

    t = time.perf_counter()
    token_counts = [len(enc.encode(c.text)) for c in all_chunks]
    with psycopg.connect(get_settings().database_url) as conn:
        apply_schema(conn)
        ensure_repo_and_commit(conn, url=url, name=name, commit_sha=full_sha)
        inserted = write_chunks(conn, all_chunks, embeddings, token_counts)
    timings["write"] = time.perf_counter() - t

    timings["total"] = time.perf_counter() - t0
    return {
        "url": url,
        "full_sha": full_sha,
        "files": len(files),
        "chunks": len(all_chunks),
        "inserted": inserted,
        "timings": timings,
    }
