import io
import zipfile

import pytest

from app.services.github_import import (
    GitHubImportError, files_from_zip, parse_github_url,
)


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr("owner-repo-abc123/" + name,
                        content if isinstance(content, bytes) else content.encode())
    return buf.getvalue()


def test_parse_urls():
    r = parse_github_url("https://github.com/psf/requests")
    assert (r.owner, r.repo, r.branch) == ("psf", "requests", None)
    r = parse_github_url("https://github.com/psf/requests.git")
    assert r.repo == "requests"
    r = parse_github_url("https://github.com/psf/requests/tree/main/src")
    assert r.branch == "main"
    r = parse_github_url("psf/requests", branch="dev")
    assert (r.owner, r.repo, r.branch) == ("psf", "requests", "dev")


def test_bad_url_is_rejected():
    for bad in ["", "hello", "https://gitlab.com/a/b", "https://github.com/onlyowner"]:
        with pytest.raises(GitHubImportError):
            parse_github_url(bad)


def test_zip_filtering_rules():
    data = make_zip({
        "src/app.py": "X = 1\n",
        "tests/test_app.py": "def test(): pass\n",
        "README.md": "# hi\n",
        "node_modules/lib/index.js": "var a;",
        "package-lock.json": "{}",
        "static/app.min.js": "var a;",
        "logo.png": b"\x89PNG\x00\x01",
        "data.json": b"\xff\xfe\x00bad",
        "notes.exe": "x",
    })
    files, stats = files_from_zip(data)
    paths = [p for p, _ in files]
    assert paths == ["src/app.py", "tests/test_app.py", "README.md"]   # code, then tests, then docs
    assert stats.imported == 3
    assert stats.skipped_dirs == 1
    assert stats.skipped_binary == 1
    assert stats.skipped_type >= 3


def test_file_limit_keeps_code_first(monkeypatch):
    import app.services.github_import as gi
    monkeypatch.setattr(gi, "MAX_FILES", 2)
    data = make_zip({"a.md": "x", "b.py": "x=1", "c.py": "y=2"})
    files, stats = files_from_zip(data)
    assert [p for p, _ in files] == ["b.py", "c.py"]
    assert stats.skipped_limit == 1


def test_not_a_zip():
    with pytest.raises(GitHubImportError):
        files_from_zip(b"this is not a zip")