import os
from dotenv import load_dotenv
from openai import OpenAI
from app.api.models import RetrievedChunk
from app.api.validator import validate_citations

load_dotenv()

def generate_answer(repo: str, question: str, chunks: list[RetrievedChunk]) -> dict:
    context = ""
    for i, c in enumerate(chunks):
        context += f"--- Chunk {i+1} ({c.path}:{c.start_line}-{c.end_line}) ---\n{c.text}\n\n"
        
    prompt = f"""You are a helpful code assistant. Answer the user's question about the repository '{repo}'.
You MUST use the provided code chunks to answer. Do not use outside knowledge.
When you reference code, you MUST cite it using the exact format `path:start_line-end_line`.
If the answer is not in the chunks, say "I cannot answer this based on the provided code."

Context:
{context}

Question: {question}
Answer:"""

    api_key = os.environ.get("LLM_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL")

    if not api_key:
        answer = f"[No API Key] Based on the code in {chunks[0].path}:{chunks[0].start_line}-{chunks[0].end_line}, here is how it works..."
    else:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b", # <--- UPDATED MODEL
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                timeout=30.0
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"[LLM Error] Failed to generate answer: {str(e)}"

    validation = validate_citations(answer, chunks)
    
    return {
        "answer": answer,
        "valid_citations": validation["valid"],
        "invalid_citations": validation["invalid"]
    }
