"""End-to-end ingest: clone → filter → chunk → embed → write."""
from __future__ import annotations

import time
from pathlib import Path

import psycopg
import tiktoken

from app.config import get_settings
from app.ingest.chunk import chunk_file
from app.ingest.clone import clone_repo, _resolve_sha
from app.ingest.embed import embed_texts
from app.ingest.filter import iter_source_files
from app.ingest.schema import apply_schema
from app.ingest.write import ensure_repo_and_commit, write_chunks

from app.ingest.ast_chunker import chunk_file_ast
from app.ingest.chunk import chunk_file


def _commit_exists(conn, full_sha: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM commits WHERE sha = %s", (full_sha,))
        return cur.fetchone() is not None


def run_ingest(url: str, sha: str, dest: Path, *, repo_name: str | None = None) -> dict:
    name = repo_name or url
    timings: dict[str, float] = {}
    
    # 1. Resolve SHA first (needed for DB check)
    t = time.perf_counter()
    full_sha = _resolve_sha(url, sha)
    timings["resolve_sha"] = time.perf_counter() - t

    # 2. Check DB Idempotency
    with psycopg.connect(get_settings().database_url) as conn:
        apply_schema(conn) # Ensure tables exist
        if _commit_exists(conn, full_sha):
            timings["total"] = sum(timings.values())
            timings["skipped"] = 1.0
            return {
                "url": url, "full_sha": full_sha, "files": 0, "chunks": 0,
                "inserted": 0, "timings": timings, "status": "skipped (already exists)"
            }

    t0 = time.perf_counter()

    # 3. The pipeline
    t = time.perf_counter()
    root, _ = clone_repo(url, full_sha, dest)
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
        
        # VARIANT D: AST Chunking
        ast_chunks = chunk_file_ast(text, path=rel, repo=name, commit_sha=full_sha)
        if ast_chunks:
            all_chunks.extend(ast_chunks)
        else:
            # Fallback to fixed chunking if AST fails
            all_chunks.extend(chunk_file(text, path=rel, repo=name, commit_sha=full_sha))
    timings["chunk"] = time.perf_counter() - t
    t = time.perf_counter()
    embeddings = embed_texts([c.text for c in all_chunks])
    timings["embed"] = time.perf_counter() - t

    t = time.perf_counter()
    token_counts = [len(enc.encode(c.text)) for c in all_chunks]
    with psycopg.connect(get_settings().database_url) as conn:
        ensure_repo_and_commit(conn, url=url, name=name, commit_sha=full_sha)
        inserted = write_chunks(conn, all_chunks, embeddings, token_counts)
    timings["write"] = time.perf_counter() - t

    timings["total"] = time.perf_counter() - t0
    return {
        "url": url, "full_sha": full_sha, "files": len(files), "chunks": len(all_chunks),
        "inserted": inserted, "timings": timings, "status": "success"
    }