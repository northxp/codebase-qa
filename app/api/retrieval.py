"""Core retrieval logic for /ask."""
from __future__ import annotations

import psycopg

from app.api.models import RetrievedChunk
from app.config import get_settings
from app.ingest.embed import embed_texts

_SEARCH_SQL = """
SELECT
    c.path,
    c.start_line,
    c.end_line,
    c.text,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
JOIN commits cm ON c.commit_sha = cm.sha
JOIN repos r ON cm.repo_id = r.id
WHERE r.name = %s
ORDER BY c.embedding <=> %s::vector
LIMIT %s
"""


def search_chunks(repo: str, question: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Embed the question and return the top_k most similar chunks for `repo`."""
    query_vec = embed_texts([question])[0].tolist()

    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(_SEARCH_SQL, (query_vec, repo, query_vec, top_k))
            rows = cur.fetchall()

    return [
        RetrievedChunk(
            path=row[0],
            start_line=row[1],
            end_line=row[2],
            text=row[3],
            similarity=round(float(row[4]), 4),
        )
        for row in rows
    ]
