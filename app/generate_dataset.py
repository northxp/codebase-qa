import ast
import json
from pathlib import Path

REPOS = {
    "requests": "data/psf_requests",
    "click": "data/pallets_click",
    "httpx": "data/encode_httpx",
    "flask": "data/pallets_flask",
    "scrapy": "data/scrapy_scrapy",
}

for repo_name, repo_path in REPOS.items():
    root = Path(repo_path)
    if not root.exists():
        print(f"Skipping {repo_name}, not cloned yet.")
        continue
        
    questions = []
    
    # 1. Generate 50 Lookup questions using AST
    for py_file in root.rglob("*.py"):
        if "test" in py_file.name or "tests" in py_file.parts:
            continue
            
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
            
        rel_path = str(py_file.relative_to(root))
        
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"): continue
                
                questions.append({
                    "id": f"lookup_{len(questions):02d}",
                    "type": "lookup",
                    "question": f"Where is {node.name} implemented?",
                    "gold_paths": [rel_path]
                })
                if len(questions) >= 50:
                    break
        if len(questions) >= 50:
            break
            
    # 2. Add 10 manual (placeholder) behavior/cross_file/unanswerable
    questions.extend([
        {"id": "beh_01", "type": "behavior", "question": f"How does {repo_name} work?", "gold_paths": []},
        {"id": "beh_02", "type": "behavior", "question": f"What are the main components of {repo_name}?", "gold_paths": []},
        {"id": "beh_03", "type": "behavior", "question": f"How is error handling done in {repo_name}?", "gold_paths": []},
        {"id": "beh_04", "type": "behavior", "question": f"How does {repo_name} handle configuration?", "gold_paths": []},
        {"id": "beh_05", "type": "behavior", "question": f"How does {repo_name} manage state?", "gold_paths": []},
        {"id": "cross_01", "type": "cross_file", "question": f"How does a request flow through {repo_name}?", "gold_paths": []},
        {"id": "cross_02", "type": "cross_file", "question": f"How do modules interact in {repo_name}?", "gold_paths": []},
        {"id": "cross_03", "type": "cross_file", "question": f"What is the entry point for {repo_name}?", "gold_paths": []},
        {"id": "cross_04", "type": "cross_file", "question": f"How are dependencies injected in {repo_name}?", "gold_paths": []},
        {"id": "unans_01", "type": "unanswerable", "question": f"How does {repo_name} implement quantum computing?", "gold_paths": []}
    ])
    
    out_path = Path(f"data/questions/{repo_name}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(questions, indent=2))
    print(f"Generated {len(questions)} questions for {repo_name}")
