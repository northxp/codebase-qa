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

def _get_source(lines: list[str], start_line: int, end_line: int) -> str:
    return "".join(lines[start_line - 1 : end_line])

def _make_chunk(lines, node, path, repo, sha, idx, class_name=None):
    docstring = ast.get_docstring(node) or ""
    source = _get_source(lines, node.lineno, node.end_lineno)
    
    prefix = f"File: {path}\n"
    if class_name:
        prefix += f"Class: {class_name}\nName: {node.name}\n"
        symbol = f"{class_name}.{node.name}"
    else:
        prefix += f"Name: {node.name}\n"
        symbol = node.name
        
    if docstring:
        prefix += f"Docstring: {docstring.strip()[:200]}...\n"
        
    chunk_text = prefix + source
    if len(chunk_text) > 4000: 
        chunk_text = chunk_text[:4000] + "\n# ... (truncated)"

    return ASTChunk(
        text=chunk_text,
        path=path,
        start_line=node.lineno,
        end_line=node.end_lineno,
        symbol_name=symbol,
        repo=repo,
        commit_sha=sha,
        chunk_index=idx
    )

def chunk_file_ast(text: str, *, path: str, repo: str, commit_sha: str) -> list[ASTChunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    lines = text.splitlines(keepends=True)
    chunks: list[ASTChunk] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # 1. Class header only (up to the first method)
            if node.body:
                first_fn = next((child for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
                header_end = first_fn.lineno - 1 if first_fn else node.end_lineno
            else:
                header_end = node.end_lineno
            
            header_source = _get_source(lines, node.lineno, header_end)
            docstring = ast.get_docstring(node) or ""
            prefix = f"File: {path}\nClass: {node.name}\nDocstring: {docstring.strip()[:200]}...\n"
            
            chunks.append(ASTChunk(
                text=prefix + header_source,
                path=path,
                start_line=node.lineno,
                end_line=header_end,
                symbol_name=node.name,
                repo=repo,
                commit_sha=commit_sha,
                chunk_index=len(chunks)
            ))
            
            # 2. Individual methods
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(_make_chunk(lines, child, path, repo, commit_sha, len(chunks), class_name=node.name))
                    
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_make_chunk(lines, node, path, repo, commit_sha, len(chunks)))
            
    return chunks
