"""Postgres schema for the codebase-qa index."""
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
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
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
        symbol_name TEXT,
        UNIQUE (commit_sha, path, chunk_index)
    )
    """,

    """
    CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    """,
    
    """
    CREATE INDEX IF NOT EXISTS chunks_symbol_name_idx
    ON chunks (symbol_name)
    """,
]


def apply_schema(conn) -> None:
    with conn.cursor() as cur:
        for stmt in _STATEMENTS:
            cur.execute(stmt)
