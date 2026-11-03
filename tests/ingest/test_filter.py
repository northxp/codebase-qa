from pathlib import Path

from app.ingest.filter import MAX_FILE_BYTES, iter_source_files


def _write(path: Path, content: str = "x = 1\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _rel_set(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in iter_source_files(root)}


def test_yields_py_files_and_skips_other_extensions(tmp_path):
    _write(tmp_path / "a.py")
    _write(tmp_path / "pkg" / "b.py")
    _write(tmp_path / "readme.md", "# not python\n")
    files = _rel_set(tmp_path)
    assert Path("a.py") in files
    assert Path("pkg/b.py") in files
    assert Path("readme.md") not in files


def test_excludes_tests_dir(tmp_path):
    _write(tmp_path / "src" / "a.py")
    _write(tmp_path / "tests" / "b.py")
    files = _rel_set(tmp_path)
    assert Path("src/a.py") in files
    assert Path("tests/b.py") not in files


def test_includes_file_named_tests_py(tmp_path):
    """Filename containing 'test' is NOT excluded — only the directory is."""
    _write(tmp_path / "mytests.py")
    assert Path("mytests.py") in _rel_set(tmp_path)


def test_excludes_nested_tests_dir(tmp_path):
    _write(tmp_path / "pkg" / "mod.py")
    _write(tmp_path / "pkg" / "tests" / "hidden.py")
    files = _rel_set(tmp_path)
    assert Path("pkg/mod.py") in files
    assert Path("pkg/tests/hidden.py") not in files


def test_excludes_huge_files(tmp_path):
    big = tmp_path / "big.py"
    big.parent.mkdir(parents=True, exist_ok=True)
    big.write_bytes(b"x" * (MAX_FILE_BYTES + 100))
    _write(tmp_path / "small.py", "y = 2\n")
    files = {p.name for p in iter_source_files(tmp_path)}
    assert "small.py" in files
    assert "big.py" not in files


def test_excludes_dot_git_dir(tmp_path):
    _write(tmp_path / ".git" / "weird.py")  # pathological .py inside .git
    _write(tmp_path / "real.py")
    files = _rel_set(tmp_path)
    assert Path("real.py") in files
    assert Path(".git/weird.py") not in files
