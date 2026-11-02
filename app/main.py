from fastapi import FastAPI

app = FastAPI(title="codebase-qa")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
