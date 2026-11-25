from fastapi import FastAPI, Request, Form, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg
from app.config import get_settings

from app.api.models import AskRequest
from app.api.retrieval import search_chunks
from app.api.generator import generate_answer
from app.auth import hash_password, verify_password, create_session, get_user_from_session

app = FastAPI(title="codebase-qa")
templates = Jinja2Templates(directory="templates")

# --- UI & Auth Routes ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = get_user_from_session(request.cookies.get("session"))
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html")

@app.post("/auth/signup")
def signup(username: str = Form(...), password: str = Form(...)):
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hash_password(password)))
            except psycopg.errors.UniqueViolation:
                raise HTTPException(400, "Username already exists")
    
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", create_session(username), httponly=True)
    return resp

@app.post("/auth/login")
def login(username: str = Form(...), password: str = Form(...)):
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if not row or not verify_password(password, row[0]):
                raise HTTPException(401, "Invalid credentials")
                
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", create_session(username), httponly=True)
    return resp

@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
    return resp

# --- HTMX Ask Endpoint ---

@app.post("/ask-ui", response_class=HTMLResponse)
def ask_ui(request: Request, repo: str = Form(...), question: str = Form(...)):
    user = get_user_from_session(request.cookies.get("session"))
    if not user:
        return HTMLResponse("<p style='color:red'>Please log in.</p>")
        
    chunks = search_chunks(repo, question, top_k=3)
    if not chunks:
        return HTMLResponse("<p>No results found.</p>")
        
    result = generate_answer(repo, question, chunks)
    
    return templates.TemplateResponse(
        request=request, 
        name="answer.html", 
        context={
            "answer": result["answer"],
            "valid_citations": result["valid_citations"]
        }
    )

# --- Existing JSON API (keep for the eval script) ---

@app.post("/ask")
def ask_json(req: AskRequest):
    chunks = search_chunks(req.repo, req.question, req.top_k)
    if not chunks: raise HTTPException(404, "No chunks found")
    llm_result = generate_answer(req.repo, req.question, chunks)
    return {
        "repo": req.repo, "question": req.question, "chunks": chunks,
        "answer": llm_result["answer"],
        "valid_citations": llm_result["valid_citations"],
        "invalid_citations": llm_result["invalid_citations"]
    }

@app.get("/health")
def health(): return {"status": "ok"}
