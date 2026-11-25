import json
from pathlib import Path
from app.api.retrieval import search_chunks

questions = json.loads(Path("data/questions/requests.json").read_text())
failures = []

print("Analyzing failures on psf/requests...")
for q in questions:
    if not q["gold_paths"]: continue
    
    chunks = search_chunks("psf/requests", q["question"], top_k=5)
    retrieved_paths = [c.path for c in chunks]
    gold = q["gold_paths"][0]
    
    if gold not in retrieved_paths:
        failures.append({
            "id": q["id"],
            "question": q["question"],
            "gold": gold,
            "retrieved": retrieved_paths
        })

print(f"\nFound {len(failures)} failures out of {len([q for q in questions if q['gold_paths']])} valid questions.")
for f in failures:
    print(f"\n[FAIL] {f['id']}: {f['question']}")
    print(f"  Gold:      {f['gold']}")
    print(f"  Retrieved: {f['retrieved']}")
