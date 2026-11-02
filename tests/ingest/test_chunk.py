import tiktoken

from app.ingest.chunk import chunk_file

BASE_KWARGS = dict(path="x.py", repo="test/repo", commit_sha="abc123")


def _count_tokens(text: str) -> int:
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


def test_empty_file_returns_no_chunks():
    assert chunk_file("", **BASE_KWARGS) == []


def test_small_file_single_chunk():
    text = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    chunks = chunk_file(text, **BASE_KWARGS)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 5
    assert chunks[0].chunk_index == 0


def test_large_file_splits_and_preserves_data():
    # ~200 lines of "x = 1\n" — comfortably >512 tokens
    text = "x = 1\n" * 200
    chunks = chunk_file(text, **BASE_KWARGS)
    assert len(chunks) >= 2
    # Invariant 1: concatenation reconstructs the original
    assert "".join(c.text for c in chunks) == text
    # Invariant 2: consecutive chunks are contiguous
    for i in range(len(chunks) - 1):
        assert chunks[i].end_line + 1 == chunks[i + 1].start_line
        assert chunks[i].chunk_index + 1 == chunks[i + 1].chunk_index
    # Every chunk respects the token budget
    for c in chunks:
        assert _count_tokens(c.text) <= 512


def test_line_numbers_are_exact():
    text = "".join(f"line{i}\n" for i in range(1, 500))
    chunks = chunk_file(text, **BASE_KWARGS)
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 499
    # Every chunk's text, when split into lines, matches the lines it claims
    for c in chunks:
        expected_lines = text.splitlines(keepends=True)[c.start_line - 1 : c.end_line]
        assert c.text == "".join(expected_lines)


def test_char_offsets_match_text():
    text = "x = 1\n" * 200
    chunks = chunk_file(text, **BASE_KWARGS)
    for c in chunks:
        assert text[c.char_start : c.char_end] == c.text


def test_long_line_splits_at_token_boundaries():
    # One line that genuinely exceeds 512 tokens: unique words don't compress
    big_line = " ".join(f"word{i}" for i in range(1000)) + "\n"
    # Assert the premise: this line MUST be > 512 tokens, or the test is vacuous
    assert _count_tokens(big_line) > 512, "test input isn't actually long enough"

    text = big_line + "y = 1\n"
    chunks = chunk_file(text, **BASE_KWARGS)
    assert len(chunks) >= 2

    # All sub-chunks of the long line report line 1
    long_line_chunks = [c for c in chunks if c.start_line == 1]
    assert len(long_line_chunks) >= 2
    for c in long_line_chunks:
        assert c.start_line == c.end_line == 1
        assert _count_tokens(c.text) <= 512

    # The trailing small line is still a chunk
    assert chunks[-1].start_line == 2