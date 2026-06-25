"""Ingest source code from a GitHub URL (clone) or an uploaded ZIP (extract)."""
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass

# Decompression-bomb guards for ZIP extraction (50MB compressed can expand huge).
MAX_ZIP_UNCOMPRESSED = 500 * 1024 * 1024  # 500 MB total uncompressed
MAX_ZIP_ENTRIES = 20000


@dataclass
class IngestResult:
    root_dir: str  # directory that holds the source code to analyse
    cleanup_dir: str  # directory to remove once judging is done


def ingest_github(url: str, workdir: str) -> IngestResult:
    """Shallow-clone a public GitHub repository into a temp directory."""
    os.makedirs(workdir, exist_ok=True)
    dest = tempfile.mkdtemp(prefix="repo_", dir=workdir)
    # Never prompt for credentials (a private/invalid URL would otherwise hang
    # until timeout); GIT_TERMINAL_PROMPT/ASKPASS make auth fail fast.
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
        "GCM_INTERACTIVE": "never",
    }
    try:
        subprocess.run(
            # "--" stops option parsing so a URL can't be treated as a git flag.
            ["git", "clone", "--depth", "1", "--", url, dest],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(dest, ignore_errors=True)
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        msg = detail[-1] if detail else "알 수 없는 오류"
        raise ValueError(f"GitHub 클론 실패: {msg}")
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        raise ValueError("GitHub 클론 시간 초과 (180초)")
    return IngestResult(root_dir=dest, cleanup_dir=dest)


def ingest_zip(zip_path: str, workdir: str) -> IngestResult:
    """Safely extract an uploaded ZIP archive into a temp directory."""
    os.makedirs(workdir, exist_ok=True)
    dest = tempfile.mkdtemp(prefix="zip_", dir=workdir)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            _safe_extract(zf, dest)
    except zipfile.BadZipFile:
        shutil.rmtree(dest, ignore_errors=True)
        raise ValueError("유효하지 않은 ZIP 파일입니다.")
    return IngestResult(root_dir=_effective_root(dest), cleanup_dir=dest)


def _safe_extract(zf: zipfile.ZipFile, dest: str) -> None:
    """Extract guarding against path-traversal (zip-slip) and decompression bombs."""
    dest_abs = os.path.abspath(dest)
    infos = zf.infolist()
    if len(infos) > MAX_ZIP_ENTRIES:
        raise ValueError("ZIP 항목 수가 너무 많습니다.")
    total = 0
    for member in infos:
        target = os.path.abspath(os.path.join(dest, member.filename))
        if target != dest_abs and not target.startswith(dest_abs + os.sep):
            raise ValueError(f"안전하지 않은 ZIP 경로: {member.filename}")
        total += member.file_size
        if total > MAX_ZIP_UNCOMPRESSED:
            raise ValueError("압축 해제 용량이 너무 큽니다 (zip bomb 방지).")
    zf.extractall(dest)


def _effective_root(dest: str) -> str:
    """If the archive contains a single top-level folder, descend into it."""
    entries = [e for e in os.listdir(dest) if e != "__MACOSX"]
    if len(entries) == 1:
        sole = os.path.join(dest, entries[0])
        if os.path.isdir(sole):
            return sole
    return dest


def cleanup(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
    if not os.path.isdir(path):
        return
    # Leftovers remain: the Docker execution sandbox runs as root with a read-write
    # bind mount, so build artifacts (node_modules, __pycache__, .pytest_cache, …)
    # can be owned by uid 0. A non-root backend then can't unlink them and rmtree's
    # errors were silently swallowed, leaking workspaces without bound. Reclaim
    # ownership via a throwaway root container, then retry. Best-effort: never raise.
    if shutil.which("docker") is None:
        return
    try:
        subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{os.path.abspath(path)}:/target",
                "busybox", "chown", "-R",
                f"{os.getuid()}:{os.getgid()}", "/target",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:  # noqa: BLE001 - cleanup must not crash the pipeline
        pass
    shutil.rmtree(path, ignore_errors=True)
