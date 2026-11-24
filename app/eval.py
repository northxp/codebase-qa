"""Evaluation harness. Calculates Hit@5, Recall@10, MRR."""
import csv
import json
import sys
import time
from pathlib import Path

from app.api.retrieval import search_chunks

def evaluate(repo: str, questions_path: Path, out_csv: Path):
    questions = json.loads(questions_path.read_text())
    
    results = []
    hits_at_5 = 0
    recall_at_10 = 0
    reciprocal_ranks = []
    
    print(f"Evaluating {len(questions)} questions on {repo}...")
    
    for q in questions:
        # Retrieve top 10 (to calculate Recall@10)
        t = time.perf_counter()
        chunks = search_chunks(repo, q["question"], top_k=10)
        latency = time.perf_counter() - t
        
        retrieved_paths = [c.path for c in chunks]
        gold_paths = q["gold_paths"]
        
        # 1. Hit@5 (Does any chunk in top 5 match any gold path?)
        top_5_paths = retrieved_paths[:5]
        hit_5 = any(p in top_5_paths for p in gold_paths) if gold_paths else False
        if hit_5: hits_at_5 += 1
        
        # 2. Recall@10 (What fraction of gold paths were found in top 10?)
        # If unanswerable, skip recall.
        if gold_paths:
            found = sum(1 for p in gold_paths if p in retrieved_paths[:10])
            rec_10 = found / len(gold_paths)
            recall_at_10 += rec_10
        else:
            rec_10 = 0.0
            
        # 3. MRR (1 / rank of the *first* correct path)
        rr = 0.0
        for rank, path in enumerate(retrieved_paths, start=1):
            if path in gold_paths:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)
        
        # 4. "Not found" check for unanswerable questions
        # If unanswerable, did we retrieve things with a similarity > 0.50? (False positive)
        false_answer = False
        if not gold_paths:
            false_answer = any(c.similarity > 0.50 for c in chunks)
            if false_answer: print(f"  [FAIL] {q['id']}: False answer generated!")

        results.append({
            "id": q["id"], "type": q["type"], "hit_5": hit_5, 
            "recall_10": round(rec_10, 4), "rr": round(rr, 4), 
            "latency_ms": round(latency * 1000, 2), "false_answer": false_answer
        })
        print(f"  {q['id']:<8} Hit@5: {hit_5!s:<5} RR: {rr:.2f}")

    # Averages
    n = len(questions)
    mrr = sum(reciprocal_ranks) / n
    avg_rec_10 = recall_at_10 / n
    final_hit_5 = hits_at_5 / n
    
    print("\n" + "="*40)
    print(f"Hit@5:    {final_hit_5:.4f} ({hits_at_5}/{n})")
    print(f"Recall@10:{avg_rec_10:.4f}")
    print(f"MRR:      {mrr:.4f}")
    print("="*40)
    
    # Write to CSV
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Raw results written to {out_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.eval <repo_name>")
        sys.exit(1)
    
    repo = sys.argv[1] # e.g. "psf/requests"
    q_path = Path(f"data/questions/{repo.split('/')[-1]}.json")
    out_path = Path(f"results/raw/{time.strftime('%Y-%m-%d')}-variant-A-dev.csv")
    
    if not q_path.exists():
        print(f"Error: {q_path} not found.")
        sys.exit(1)
        
    evaluate(repo, q_path, out_path)
