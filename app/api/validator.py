"""Validates LLM citations against the chunks actually retrieved."""
import re
from app.api.models import RetrievedChunk

def validate_citations(answer: str, retrieved_chunks: list[RetrievedChunk]) -> dict:
    pattern = r'([a-zA-Z0-9_\-\./]+\.[a-zA-Z]+):(\d+)(?:-(\d+))?'
    matches = re.findall(pattern, answer)
    valid = []
    invalid = []
    
    for path, start_str, end_str in matches:
        start = int(start_str)
        end = int(end_str) if end_str else start
        
        found = False
        for c in retrieved_chunks:
            if c.path.endswith(path) or path.endswith(c.path):
                if not (end < c.start_line or start > c.end_line):
                    found = True
                    break
                    
        if found:
            valid.append(f"{path}:{start}-{end}")
        else:
            invalid.append(f"{path}:{start}-{end}")
            
    return {"valid": list(set(valid)), "invalid": list(set(invalid))}
