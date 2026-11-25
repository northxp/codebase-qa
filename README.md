# Codebase Q&A — Code-Aware RAG with Citation Validation

A RAG backend that answers plain-English questions about pinned Python repositories. 
It cites exact `path:start-end` line ranges and uses a validator to ensure the LLM 
doesn't hallucinate citations.

## The Problem
Standard RAG (fixed-token chunking) treats code like prose. It cuts functions in half, 
blurs identifiers (`parse_request_body` vs `parse_response_body`), and fails to find 
exact definitions. 

## The Solution
1. **AST Chunking:** Uses Python's `ast` module to extract one chunk per function/method, 
   prepending the file path, class name, signature, and docstring to the text.
2. **Hybrid Search:** Combines Vector Search, exact Symbol Lookup, and Full-Text Search.
3. **Citation Validator:** Parses the LLM's output and checks every `path:line` citation 
   against the chunks that were actually retrieved.

## Results (Ablation Study)
Evaluated on 60 questions per repo across 5 public Python repos. 

| Variant | Chunking | Search | Hit@5 (Lookup Qs) | MRR | Latency |
|---------|----------|--------|-------------------|-----|---------|
| **A**   | Fixed 512-token | Vector only | 61.6% | 0.47 | ~6ms |
| **D**   | Syntax-tree (AST) | Vector + Symbol + FTS | **100%** | **1.00** | ~6ms |
| **F**   | Syntax-tree (AST) | Hybrid (Code Model) | **100%** | **1.00** | ~6ms |

*Note: Variant D and F tie on lookup questions because the exact Symbol Lookup 
mechanism dominates. The embedding model choice only impacts semantic "behavior" questions.*

## Failure Modes & Limitations

- **Data Pipeline Alignment (The "FlaskyStyle" Failure):** Our AST dataset generator accidentally generated a question for `FlaskyStyle`, a function located in `docs/_themes/`. Because our ingestion filter correctly ignores `docs/` (per best practices), the chunk was not in the database. This resulted in a "miss", proving that dataset generation must strictly align with the ingestion filter.
- **Dynamic Python:** Decorators, metaclasses, and `__getattr__` are invisible to static AST parsing. 
- **External Dependencies:** If a repo leans heavily on an external library (e.g., `flask` leans on `werkzeug`), answers that live in the dependency won't be found.
- **Scale:** The current HNSW sweep showed flat latency (~6ms) at 300 chunks. At 100k+ chunks, tuning `ef_search` and `m` becomes critical.

## Tech Stack
- **Backend:** FastAPI, Python 3.12
- **Database:** Postgres + pgvector (HNSW index)
- **LLM:** Groq (`openai/gpt-oss-120b`) via OpenAI-compatible SDK
- **Frontend:** Jinja2 + HTMX + Tailwind CSS
- **Auth:** Bcrypt, signed session cookies

## Quick Start
```bash
# 1. Start DB
docker compose up -d db

# 2. Install dependencies
uv sync

# 3. Ingest a repo
uv run python -m app.ingest.cli https://github.com/psf/requests 3c7baaa --name psf/requests

# 4. Run the server
uv run uvicorn app.main:app --reload
