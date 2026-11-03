"""Postgres schema for the codebase-qa index.

Idempotent: safe to run on every pipeline invocation. All DDL uses IF NOT EXISTS.
The `commits` table records every ingested commit. `chunks` holds one row per
embedded chunk, keyed by (commit_sha, path, chunk_index) for idempotent upsert.
"""
from __future__ import annotations

from app.ingest.embed import DIM

_STATEMENTS: list[str] = [
    "CREATE EXTENSION IF NOT EXISTS vector",

    """
    CREATE TABLE IF NOT EXISTS repos (
        id SERIAL PRIMARY KEY,
        url TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS commits (
        sha TEXT PRIMARY KEY,
        repo_id INTEGER NOT NULL REFERENCES repos(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,

    f"""
    CREATE TABLE IF NOT EXISTS chunks (
        id BIGSERIAL PRIMARY KEY,
        commit_sha TEXT NOT NULL REFERENCES commits(sha),
        path TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        start_line INTEGER NOT NULL,
        end_line INTEGER NOT NULL,
        char_start INTEGER NOT NULL,
        char_end INTEGER NOT NULL,
        text TEXT NOT NULL,
        token_count INTEGER NOT NULL,
        embedding vector({DIM}) NOT NULL,
        UNIQUE (commit_sha, path, chunk_index)
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    """,
]


def apply_schema(conn) -> None:
    with conn.cursor() as cur:
        for stmt in _STATEMENTS:
            cur.execute(stmt)
