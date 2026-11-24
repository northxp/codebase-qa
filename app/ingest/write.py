"""Insert commits and chunks into Postgres.

All functions take an existing connection; none commit. The caller wraps the
whole ingest in one transaction for atomicity.
"""
from __future__ import annotations

import numpy as np
import psycopg

from app.ingest.chunk import Chunk


_INSERT_CHUNK = """
INSERT INTO chunks (
    commit_sha, path, chunk_index, start_line, end_line,
    char_start, char_end, text, token_count, embedding, symbol_name
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (commit_sha, path, chunk_index) DO NOTHING
"""


def ensure_repo_and_commit(
    conn: psycopg.Connection,
    *,
    url: str,
    name: str,
    commit_sha: str,
) -> int:
    """Upsert repo + commit rows. Returns repo_id."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO repos (url, name) VALUES (%s, %s) "
            "ON CONFLICT (url) DO NOTHING",
            (url, name),
        )
        cur.execute("SELECT id FROM repos WHERE url = %s", (url,))
        repo_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO commits (sha, repo_id) VALUES (%s, %s) "
            "ON CONFLICT (sha) DO NOTHING",
            (commit_sha, repo_id),
        )
    return repo_id


def write_chunks(conn, chunks, embeddings, token_counts):
    if not chunks:
        return 0
    rows = [
        (
            c.commit_sha, c.path, c.chunk_index, c.start_line, c.end_line,
            getattr(c, 'char_start', 0), getattr(c, 'char_end', 0), 
            c.text, tok, emb.tolist(), getattr(c, 'symbol_name', None)
        )
        for c, tok, emb in zip(chunks, token_counts, embeddings)
    ]
    with conn.cursor() as cur:
        cur.executemany(_INSERT_CHUNK, rows)
        return cur.rowcount
