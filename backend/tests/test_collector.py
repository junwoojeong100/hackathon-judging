import os

from app.services.collector import build_digest


def test_build_digest_filters_and_prioritizes(tmp_path):
    (tmp_path / "README.md").write_text("# Hello\nproject")
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hi')")
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "lib.js").write_text("ignored dependency")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\x00\x00binary")

    digest = build_digest(
        str(tmp_path), max_files=50, max_file_chars=1000, max_total_chars=10000
    )
    paths = [f["path"] for f in digest.files]

    assert "README.md" in paths
    assert os.path.join("src", "main.py") in paths
    assert all("node_modules" not in p for p in paths)
    assert all(not p.endswith(".png") for p in paths)
    # README is highest priority -> first
    assert digest.files[0]["path"] == "README.md"


def test_build_digest_truncates_large_file(tmp_path):
    (tmp_path / "big.py").write_text("x" * 5000)
    digest = build_digest(
        str(tmp_path), max_files=50, max_file_chars=100, max_total_chars=10000
    )
    content = digest.files[0]["content"]
    assert content.endswith("[truncated]")
    assert len(content) <= 120


def test_build_digest_respects_total_cap(tmp_path):
    for i in range(10):
        (tmp_path / f"f{i}.py").write_text("a" * 500)
    digest = build_digest(
        str(tmp_path), max_files=50, max_file_chars=500, max_total_chars=600
    )
    assert digest.truncated is True
    assert digest.total_chars <= 600
