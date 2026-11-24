"""Code-aware chunker using Python's ast module (Variant D)."""
from __future__ import annotations
import ast
from dataclasses import dataclass

@dataclass(frozen=True)
class ASTChunk:
    text: str
    path: str
    start_line: int
    end_line: int
    symbol_name: str
    repo: str
    commit_sha: str
    chunk_index: int

def _get_source(lines: list[str], node: ast.AST) -> str:
    return "".join(lines[node.lineno - 1 : node.end_lineno])

def chunk_file_ast(text: str, *, path: str, repo: str, commit_sha: str) -> list[ASTChunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    lines = text.splitlines(keepends=True)
    chunks: list[ASTChunk] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            docstring = ast.get_docstring(node) or ""
            source = _get_source(lines, node)
            
            # Prepend context to the embedding
            prefix = f"File: {path}\nName: {node.name}\n"
            if docstring:
                prefix += f"Docstring: {docstring.strip()[:200]}...\n"
            
            chunk_text = prefix + source
            if len(chunk_text) > 4000: 
                chunk_text = chunk_text[:4000] + "\n# ... (truncated)"

            chunks.append(
                ASTChunk(
                    text=chunk_text,
                    path=path,
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                    symbol_name=node.name,
                    repo=repo,
                    commit_sha=commit_sha,
                    chunk_index=len(chunks)
                )
            )
    return chunks
