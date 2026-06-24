"""Walk an ingested source tree, filter noise, and build a size-bounded digest
that fits within the LLM context window."""
import os
from dataclasses import dataclass, field

SKIP_DIRS = {
    ".git", ".github", ".svn", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", "out", "target", ".idea", ".vscode",
    "vendor", ".gradle", "bin", "obj", ".pytest_cache", "coverage", ".nyc_output",
    ".mypy_cache", "__MACOSX", "Pods", "DerivedData", ".terraform", ".cache",
    "site-packages", "migrations",
}

CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".rb",
    ".php", ".c", ".cpp", ".cc", ".h", ".hpp", ".cs", ".swift", ".m", ".mm",
    ".scala", ".sh", ".bash", ".sql", ".html", ".css", ".scss", ".vue", ".svelte",
    ".dart", ".r", ".jl", ".lua", ".ex", ".exs", ".clj", ".yaml", ".yml",
    ".toml", ".json", ".tf", ".proto", ".gradle",
}

DOC_EXTS = {".md", ".rst", ".txt", ".adoc"}

SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf", ".zip",
    ".gz", ".tar", ".rar", ".7z", ".mp4", ".mov", ".avi", ".mp3", ".wav",
    ".ttf", ".otf", ".woff", ".woff2", ".eot", ".class", ".jar", ".war",
    ".exe", ".dll", ".so", ".dylib", ".o", ".a", ".pyc", ".pyo", ".lock",
    ".bin", ".db", ".sqlite", ".sqlite3", ".ipynb", ".map", ".min.js", ".min.css",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "cargo.lock", "gemfile.lock", "composer.lock", ".ds_store", "go.sum",
}

NO_EXT_KEEP = {"dockerfile", "makefile", "readme", "license", "procfile"}
PRIORITY_STEMS = {"main", "app", "index", "server", "__init__", "cli"}

MAX_RAW_READ = 400_000  # don't read more than this many bytes from one file


@dataclass
class CodeDigest:
    file_tree: str
    files: list = field(default_factory=list)  # [{"path": str, "content": str}]
    total_files_seen: int = 0
    included_files: int = 0
    total_chars: int = 0
    truncated: bool = False


def _is_candidate(name: str) -> bool:
    lower = name.lower()
    if lower in SKIP_FILES:
        return False
    ext = os.path.splitext(lower)[1]
    if ext in SKIP_EXTS:
        return False
    if ext in CODE_EXTS or ext in DOC_EXTS:
        return True
    if lower in NO_EXT_KEEP or os.path.splitext(lower)[0] in NO_EXT_KEEP:
        return True
    return False


def _priority(rel: str) -> tuple:
    name = os.path.basename(rel).lower()
    stem, ext = os.path.splitext(name)
    depth = rel.count(os.sep)
    if stem.startswith("readme"):
        return (0, depth)
    if ext in DOC_EXTS:
        return (1, depth)
    if stem in PRIORITY_STEMS or name in ("dockerfile", "makefile"):
        return (2, depth)
    if ext in CODE_EXTS:
        return (3, depth)
    return (4, depth)


def _read_text(path: str, limit: int) -> str | None:
    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_RAW_READ)
    except OSError:
        return None
    if b"\x00" in raw:  # looks binary
        return None
    text = raw.decode("utf-8", errors="replace")
    if len(text) > limit:
        text = text[:limit] + "\n... [truncated]"
    return text


def build_digest(
    root_dir: str,
    max_files: int,
    max_file_chars: int,
    max_total_chars: int,
) -> CodeDigest:
    candidates: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fn in filenames:
            if _is_candidate(fn):
                candidates.append(os.path.relpath(os.path.join(dirpath, fn), root_dir))

    candidates.sort(key=lambda r: (_priority(r), r))

    tree_lines = sorted(candidates)
    if len(tree_lines) > 400:
        tree_lines = tree_lines[:400] + [f"... (+{len(candidates) - 400} more files)"]
    file_tree = "\n".join(tree_lines)

    digest = CodeDigest(file_tree=file_tree, total_files_seen=len(candidates))

    for rel in candidates:
        if digest.included_files >= max_files:
            digest.truncated = True
            break
        if digest.total_chars >= max_total_chars:
            digest.truncated = True
            break
        content = _read_text(os.path.join(root_dir, rel), max_file_chars)
        if content is None or not content.strip():
            continue
        remaining = max_total_chars - digest.total_chars
        marker = "\n... [truncated]"
        if len(content) > remaining:
            cut = remaining - len(marker)
            if cut <= 0:
                digest.truncated = True
                break
            content = content[:cut] + marker
            digest.truncated = True
        digest.files.append({"path": rel, "content": content})
        digest.included_files += 1
        digest.total_chars += len(content)

    return digest


def render_digest(digest: CodeDigest) -> str:
    """Render the digest into a single prompt-friendly string."""
    parts = ["# 파일 트리\n", digest.file_tree, "\n\n# 파일 내용\n"]
    for f in digest.files:
        parts.append(f"\n----- FILE: {f['path']} -----\n{f['content']}\n")
    if digest.truncated:
        parts.append(
            "\n[참고: 저장소가 커서 일부 파일/내용은 생략되었습니다. "
            "위 파일 트리로 전체 범위를 참고하세요.]\n"
        )
    return "".join(parts)
