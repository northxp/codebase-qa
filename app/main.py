from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import psycopg
import subprocess
import uuid
from app.config import get_settings
from app.api.retrieval import search_chunks
from app.api.generator import generate_answer
from app.auth import hash_password, verify_password, create_session, get_user_from_session
from app.ingest.pipeline import run_ingest
from pathlib import Path

app = FastAPI(title="codebase-qa")
templates = Jinja2Templates(directory="templates")

INGEST_PROGRESS = {}

def get_latest_sha(url: str) -> str:
    res = subprocess.run(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True)
    if res.returncode != 0: raise Exception("Invalid repo URL")
    return res.stdout.split()[0]

def current_user(request: Request):
    return get_user_from_session(request.cookies.get("session"))

def parse_repo_name(url: str) -> str:
    clean_url = url.rstrip("/")
    if clean_url.endswith(".git"):
        clean_url = clean_url[:-4]
    parts = clean_url.split("/")
    return f"{parts[-2]}/{parts[-1]}"

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = current_user(request)
    if not user: return RedirectResponse("/login")
    
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM repos ORDER BY name")
            repos = [r[0] for r in cur.fetchall()]
            
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user, "repos": repos})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse(request=request, name="login.html")

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request): return templates.TemplateResponse(request=request, name="signup.html")

@app.post("/auth/signup")
def signup(username: str = Form(...), password: str = Form(...)):
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING role", (username, hash_password(password)))
                role = cur.fetchone()[0]
            except psycopg.errors.UniqueViolation:
                raise HTTPException(400, "Username already exists")
    
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", create_session(username, role), httponly=True)
    return resp

@app.post("/auth/login")
def login(username: str = Form(...), password: str = Form(...)):
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash, role FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
            if not row or not verify_password(password, row[0]): raise HTTPException(401, "Invalid credentials")
                
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", create_session(username, row[1]), httponly=True)
    return resp

@app.post("/auth/admin-login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if username != "admin" or password != "admin":
        raise HTTPException(401, "Invalid admin credentials")
    
    resp = RedirectResponse("/admin", status_code=303)
    resp.set_cookie("session", create_session("admin", "admin"), httponly=True)
    return resp

@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
    return resp

@app.post("/ask-ui", response_class=HTMLResponse)
def ask_ui(request: Request, repo: str = Form(...), question: str = Form(...)):
    user = current_user(request)
    if not user: return HTMLResponse("<p class='text-red-500'>Please log in.</p>")
        
    chunks = search_chunks(repo, question, top_k=3)
    
    # If no chunks are found, return an AI-styled error message
    if not chunks: 
        return HTMLResponse("""
            <div class="flex gap-4 mb-6">
                <div class="w-8 h-8 rounded-full bg-white flex-shrink-0 flex items-center justify-center shadow-sm mt-1">
                    <span class="text-black font-bold text-xs">AI</span>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="text-zinc-300 text-[15px] leading-relaxed">
                        I couldn't find any Python code in this repository to answer your question.
                    </div>
                </div>
            </div>
        """)
        
    result = generate_answer(repo, question, chunks)
    
    return templates.TemplateResponse(request=request, name="answer.html", context={
        "answer": result["answer"],
        "valid_citations": result["valid_citations"],
        "loop": {"index": str(uuid.uuid4())[:8]}
    })

# --- Admin Routes ---
@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    user = current_user(request)
    if not user or user["role"] != "admin": raise HTTPException(403, "Admin only")
    
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT r.name, c.sha, c.created_at FROM repos r JOIN commits c ON r.id = c.repo_id ORDER BY c.created_at DESC")
            repos = cur.fetchall()
            
    return templates.TemplateResponse(request=request, name="admin.html", context={"user": user, "repos": repos})

def background_ingest(job_id: str, url: str, sha: str, dest: Path, repo_name: str):
    def cb(msg):
        INGEST_PROGRESS[job_id] = msg
    try:
        run_ingest(url, sha, dest, repo_name=repo_name, progress_cb=cb)
    except Exception as e:
        INGEST_PROGRESS[job_id] = f"Error: {str(e)}"

@app.post("/admin/ingest")
def admin_ingest(request: Request, background_tasks: BackgroundTasks, url: str = Form(...), sha: str = Form(None)):
    user = current_user(request)
    if not user or user["role"] != "admin": raise HTTPException(403, "Admin only")
    
    try:
        if not sha or sha.strip() == "":
            sha = get_latest_sha(url)
        
        repo_name = parse_repo_name(url)
        dest = Path(f"data/{repo_name.replace('/', '_')}")
        
        job_id = str(uuid.uuid4())[:8]
        INGEST_PROGRESS[job_id] = "Starting..."
        
        background_tasks.add_task(background_ingest, job_id, url, sha, dest, repo_name)
        
        return HTMLResponse(f"""
            <div hx-get="/admin/progress/{job_id}" hx-trigger="every 1s" hx-swap="innerHTML" 
                 class="mt-4 p-4 bg-app border border-border rounded-xl flex items-center gap-3">
                <div class="w-4 h-4 border-2 border-zinc-500 border-t-white rounded-full animate-spin"></div>
                <span class="text-sm text-zinc-300 font-medium">Starting ingestion...</span>
            </div>
        """)
    except Exception as e:
        return HTMLResponse(f"<div class='text-red-400 text-sm mt-4'>Error: {str(e)}</div>")

@app.get("/admin/progress/{job_id}")
def admin_progress(job_id: str):
    msg = INGEST_PROGRESS.get(job_id, "Unknown status")
    if msg == "Done!":
        return HTMLResponse(f"""
            <div class="mt-4 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-3">
                <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                <span class="text-sm text-emerald-400 font-medium">Successfully ingested!</span>
                <button onclick="window.location.reload()" class="ml-auto text-xs bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 px-3 py-1.5 rounded-lg transition-colors">Refresh</button>
            </div>
        """)
    elif msg.startswith("Error"):
        return HTMLResponse(f"""
            <div class="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3">
                <span class="text-sm text-red-400 font-medium">{msg}</span>
            </div>
        """)
    else:
        return HTMLResponse(f"""
            <div class="mt-4 p-4 bg-app border border-border rounded-xl flex items-center gap-3">
                <div class="w-4 h-4 border-2 border-zinc-500 border-t-white rounded-full animate-spin"></div>
                <span class="text-sm text-zinc-300 font-medium">{msg}</span>
            </div>
        """)

@app.post("/admin/delete-repo")
def delete_repo(request: Request, repo_name: str = Form(...)):
    user = current_user(request)
    if not user or user["role"] != "admin": raise HTTPException(403, "Admin only")
    
    with psycopg.connect(get_settings().database_url) as conn:
        with conn.cursor() as cur:
            # 1. Get repo_id
            cur.execute("SELECT id FROM repos WHERE name = %s", (repo_name,))
            row = cur.fetchone()
            if row:
                repo_id = row[0]
                # 2. Get all commit SHAs for this repo
                cur.execute("SELECT sha FROM commits WHERE repo_id = %s", (repo_id,))
                shas = [r[0] for r in cur.fetchall()]
                
                # 3. Delete chunks (Foreign Key)
                if shas:
                    cur.execute("DELETE FROM chunks WHERE commit_sha = ANY(%s)", (shas,))
                    
                # 4. Delete commits
                cur.execute("DELETE FROM commits WHERE repo_id = %s", (repo_id,))
                
                # 5. Delete repo
                cur.execute("DELETE FROM repos WHERE id = %s", (repo_id,))
                
    return HTMLResponse("") # HTMX removes the row
