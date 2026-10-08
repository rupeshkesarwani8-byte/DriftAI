"""Import a public GitHub repository as a DriftAI project (Build 4).

Only the standard library is used (urllib + zipfile), so nothing new to install.
Flow: parse the link -> download the repo as a zip -> keep only useful text files.
"""
from __future__ import annotations

import io
import re
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field

ALLOWED_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".txt", ".json", ".html", ".css")
CODE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx")
SKIP_DIRS = {
    ".git", ".github", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build",
    ".next", ".nuxt", "vendor", "site-packages", ".idea", ".vscode", "coverage", "target",
    "bower_components", ".tox", ".mypy_cache", ".pytest_cache",
}
SKIP_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock", "poetry.lock"}
SKIP_SUFFIXES = (".min.js", ".min.css", ".map", ".bundle.js")
MAX_FILE_BYTES = 1_000_000        # same 1 MB limit as manual upload
MAX_FILES = 300
MAX_ZIP_BYTES = 40_000_000        # refuse repositories larger than ~40 MB
TIMEOUT_SECONDS = 40


class GitHubImportError(Exception):
    """Raised with a message that is safe to show to the user."""


@dataclass
class RepoRef:
    owner: str
    repo: str
    branch: str | None = None


@dataclass
class ImportStats:
    imported: int = 0
    skipped_dirs: int = 0
    skipped_type: int = 0
    skipped_big: int = 0
    skipped_binary: int = 0
    skipped_limit: int = 0
    notes: list[str] = field(default_factory=list)


_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)"
    r"(?:\.git)?(?:/tree/(?P<branch>[^/?#]+).*)?/?(?:[?#].*)?$"
)
_SHORT = re.compile(r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)$")


def parse_github_url(text: str, branch: str | None = None) -> RepoRef:
    """Accepts https://github.com/owner/repo, .../repo.git, .../tree/branch and owner/repo."""
    text = (text or "").strip()
    m = _URL.match(text) or _SHORT.match(text)
    if not m:
        raise GitHubImportError("That does not look like a GitHub repository link. "
                                "Example: https://github.com/psf/requests")
    gd = m.groupdict()
    repo = gd["repo"][:-4] if gd["repo"].endswith(".git") else gd["repo"]
    return RepoRef(gd["owner"], repo, branch or gd.get("branch"))


def download_zip(ref: RepoRef) -> bytes:
    tail = f"/{ref.branch}" if ref.branch else ""
    url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/zipball{tail}"
    req = urllib.request.Request(url, headers={"User-Agent": "DriftAI", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = resp.read(MAX_ZIP_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GitHubImportError("Repository (or branch) not found. Private repositories are not supported yet.")
        if e.code in (403, 429):
            raise GitHubImportError("GitHub rate limit reached. Wait a few minutes and try again.")
        raise GitHubImportError(f"GitHub returned an error ({e.code}).")
    except (urllib.error.URLError, TimeoutError):
        raise GitHubImportError("Could not reach GitHub. Check your internet connection and try again.")
    if len(data) > MAX_ZIP_BYTES:
        raise GitHubImportError("This repository is too large (over 40 MB). Try a smaller one.")
    return data


def _priority(path: str) -> tuple[int, str]:
    p = path.lower()
    if p.endswith(CODE_EXT) and "test" not in p:
        return (0, p)
    if p.endswith(CODE_EXT):
        return (1, p)
    return (2, p)


def files_from_zip(data: bytes) -> tuple[list[tuple[str, str]], ImportStats]:
    stats = ImportStats()
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise GitHubImportError("GitHub did not return a valid zip file.")

    candidates: list[tuple[str, str]] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        parts = info.filename.split("/")[1:]          # drop the "owner-repo-sha/" top folder
        if not parts:
            continue
        path = "/".join(parts)
        name = parts[-1]
        if any(p in SKIP_DIRS for p in parts[:-1]):
            stats.skipped_dirs += 1
            continue
        low = name.lower()
        if not low.endswith(ALLOWED_EXT) or name in SKIP_NAMES or low.endswith(SKIP_SUFFIXES):
            stats.skipped_type += 1
            continue
        if info.file_size > MAX_FILE_BYTES:
            stats.skipped_big += 1
            continue
        try:
            text = zf.read(info).decode("utf-8")
        except UnicodeDecodeError:
            stats.skipped_binary += 1
            continue
        if "\x00" in text:
            stats.skipped_binary += 1
            continue
        candidates.append((path, text))

    candidates.sort(key=lambda it: _priority(it[0]))     # real code first, then tests, then docs
    if len(candidates) > MAX_FILES:
        stats.skipped_limit = len(candidates) - MAX_FILES
        stats.notes.append(f"Only the first {MAX_FILES} files were imported (code first).")
        candidates = candidates[:MAX_FILES]
    stats.imported = len(candidates)
    return candidates, stats


def fetch_repo_files(url: str, branch: str | None = None) -> tuple[RepoRef, list[tuple[str, str]], ImportStats]:
    ref = parse_github_url(url, branch)
    files, stats = files_from_zip(download_zip(ref))
    if not files:
        raise GitHubImportError("No supported source files were found in this repository.")
    return ref, files, stats