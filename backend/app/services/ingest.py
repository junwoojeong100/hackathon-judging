"""Ingest source code from a GitHub URL (clone) or an uploaded ZIP (extract)."""
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass


@dataclass
class IngestResult:
    root_dir: str  # directory that holds the source code to analyse
    cleanup_dir: str  # directory to remove once judging is done


def ingest_github(url: str, workdir: str) -> IngestResult:
    """Shallow-clone a public GitHub repository into a temp directory."""
    os.makedirs(workdir, exist_ok=True)
    dest = tempfile.mkdtemp(prefix="repo_", dir=workdir)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, dest],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
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
    """Extract guarding against path-traversal (zip-slip)."""
    dest_abs = os.path.abspath(dest)
    for member in zf.infolist():
        target = os.path.abspath(os.path.join(dest, member.filename))
        if target != dest_abs and not target.startswith(dest_abs + os.sep):
            raise ValueError(f"안전하지 않은 ZIP 경로: {member.filename}")
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
