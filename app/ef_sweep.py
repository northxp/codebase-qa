import time
import json
from pathlib import Path
import psycopg
from app.config import get_settings
from app.ingest.embed import embed_texts

# 1. Load the questions for requests
questions = json.loads(Path("data/questions/requests.json").read_text())
# Use the 50 lookup questions for this benchmark
lookups = [q for q in questions if q["type"] == "lookup"][:20] # Just 20 to keep it fast

ef_values = [10, 40, 100]
results = []

with psycopg.connect(get_settings().database_url) as conn:
    with conn.cursor() as cur:
        for ef in ef_values:
            # Set the session parameter for the current transaction
            cur.execute(f"SET LOCAL hnsw.ef_search = {ef};")
            
            hits = 0
            latencies = []
            
            for q in lookups:
                vec = embed_texts([q["question"]])[0].tolist()
                gold_path = q["gold_paths"][0]
                
                t = time.perf_counter()
                cur.execute("""
                    SELECT path FROM chunks 
                    WHERE embedding <=> %s::vector IS NOT NULL
                    ORDER BY embedding <=> %s::vector LIMIT 10
                """, (vec, vec))
                rows = cur.fetchall()
                latencies.append((time.perf_counter() - t) * 1000)
                
                retrieved_paths = [r[0] for r in rows]
                if gold_path in retrieved_paths:
                    hits += 1
                    
            recall = hits / len(lookups)
            avg_lat = sum(latencies) / len(latencies)
            
            results.append({"ef_search": ef, "recall_at_10": recall, "latency_ms": avg_lat})
            print(f"ef_search={ef:<3} | Recall@10: {recall:.4f} | Latency: {avg_lat:.2f}ms")

Path("results/hnsw_sweep.json").write_text(json.dumps(results, indent=2))
