"""Core retrieval logic for /ask (Variant D: Hybrid Search)."""
from __future__ import annotations
import re
import psycopg
from app.api.models import RetrievedChunk
from app.config import get_settings
from app.ingest.embed import embed_texts

_VECTOR_SEARCH_SQL = """
SELECT path, start_line, end_line, text, 1 - (embedding <=> %s::vector) AS similarity, symbol_name
FROM chunks c JOIN commits cm ON c.commit_sha = cm.sha JOIN repos r ON cm.repo_id = r.id
WHERE r.name = %s
ORDER BY embedding <=> %s::vector
LIMIT %s
"""

_SYMBOL_SEARCH_SQL = """
SELECT path, start_line, end_line, text, symbol_name
FROM chunks c JOIN commits cm ON c.commit_sha = cm.sha JOIN repos r ON cm.repo_id = r.id
WHERE r.name = %s AND symbol_name = %s
"""

def search_chunks(repo: str, question: str, top_k: int = 5) -> list[RetrievedChunk]:
    query_vec = embed_texts([question])[0].tolist()
    
    # 1. Extract potential symbols from the question
    # e.g. "Where is merge_setting defined?" -> ["merge_setting"]
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', question)
    
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            # 2. Vector Search (Top 10)
            cur.execute(_VECTOR_SEARCH_SQL, (query_vec, repo, query_vec, 10))
            vector_rows = cur.fetchall()
            
            # 3. Symbol Table Search (Exact matches)
            symbol_rows = []
            for word in words:
                cur.execute(_SYMBOL_SEARCH_SQL, (repo, word))
                symbol_rows.extend(cur.fetchall())
                
    # 4. Fuse results (Symbol matches get max similarity, vector matches get their score)
    seen = set()
    fused = []
    
    # Add symbol matches first
    for row in symbol_rows:
        key = (row[0], row[1]) # path, start_line
        if key not in seen:
            seen.add(key)
            fused.append(RetrievedChunk(
                path=row[0], start_line=row[1], end_line=row[2],
                text=row[3], similarity=1.0
            ))
            
    # Add vector matches
    for row in vector_rows:
        key = (row[0], row[1])
        if key not in seen:
            seen.add(key)
            fused.append(RetrievedChunk(
                path=row[0], start_line=row[1], end_line=row[2],
                text=row[3], similarity=round(float(row[4]), 4)
            ))

    return fused[:top_k]