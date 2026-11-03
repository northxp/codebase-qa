from fastapi import FastAPI, HTTPException

from app.api.models import AskRequest, AskResponse
from app.api.retrieval import search_chunks

app = FastAPI(title="codebase-qa")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Retrieve the top-k most relevant code chunks for a question."""
    chunks = search_chunks(req.repo, req.question, req.top_k)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No indexed chunks found for repo '{req.repo}' or question.",
        )

    return AskResponse(repo=req.repo, question=req.question, chunks=chunks)
