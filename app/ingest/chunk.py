"""Fixed 512-token chunker — baseline variant A.

Deliberately naive: it does not understand Python syntax, functions, or classes.
Slices text by token count with a line-aware accumulator and a long-line fallback.
"""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken


@dataclass(frozen=True)
class Chunk:
    text: str
    path: str
    start_line: int
    end_line: int
    repo: str
    commit_sha: str
    chunk_index: int
    char_start: int
    char_end: int


def chunk_file(
    text: str,
    *,
    path: str,
    repo: str,
    commit_sha: str,
    max_tokens: int = 512,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    if not text:
        return []

    enc = tiktoken.get_encoding(encoding_name)
    lines = text.splitlines(keepends=True)

    chunks: list[Chunk] = []
    cur_lines: list[str] = []
    cur_tokens = 0
    cur_start_line = 1
    cur_start_char = 0
    cur_char = 0

    def flush(end_line: int) -> None:
        nonlocal cur_lines, cur_tokens, cur_start_line, cur_start_char
        if not cur_lines:
            return
        chunk_text = "".join(cur_lines)
        chunks.append(
            Chunk(
                text=chunk_text,
                path=path,
                start_line=cur_start_line,
                end_line=end_line,
                repo=repo,
                commit_sha=commit_sha,
                chunk_index=len(chunks),
                char_start=cur_start_char,
                char_end=cur_start_char + len(chunk_text),
            )
        )
        cur_lines = []
        cur_tokens = 0

    for line_no, line in enumerate(lines, start=1):
        line_tokens = len(enc.encode(line))

        if line_tokens > max_tokens:
            # Pathological long line: flush pending, split this line at token boundaries.
            flush(end_line=line_no - 1)
            token_ids = enc.encode(line)
            offset = 0
            for j in range(0, len(token_ids), max_tokens):
                piece = enc.decode(token_ids[j : j + max_tokens])
                piece_len = len(piece)
                chunks.append(
                    Chunk(
                        text=piece,
                        path=path,
                        start_line=line_no,
                        end_line=line_no,
                        repo=repo,
                        commit_sha=commit_sha,
                        chunk_index=len(chunks),
                        char_start=cur_char + offset,
                        char_end=cur_char + offset + piece_len,
                    )
                )
                offset += piece_len
            cur_char += len(line)
            cur_start_line = line_no + 1
            cur_start_char = cur_char
            continue

        if cur_lines and cur_tokens + line_tokens > max_tokens:
            flush(end_line=line_no - 1)
            cur_start_line = line_no
            cur_start_char = cur_char

        if not cur_lines:
            cur_start_line = line_no
            cur_start_char = cur_char

        cur_lines.append(line)
        cur_tokens += line_tokens
        cur_char += len(line)

    flush(end_line=len(lines))
    return chunks
