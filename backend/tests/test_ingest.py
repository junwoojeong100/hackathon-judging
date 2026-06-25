import os
import tempfile

from app.services import ingest


def test_cleanup_removes_normal_dir():
    d = tempfile.mkdtemp()
    open(os.path.join(d, "f.txt"), "w").close()
    ingest.cleanup(d)
    assert not os.path.exists(d)


def test_cleanup_no_docker_call_on_success(monkeypatch):
    # Happy path: when the first rmtree succeeds, no Docker reclaim is attempted.
    called = {"which": False}

    def fake_which(_):
        called["which"] = True
        return "/usr/bin/docker"

    monkeypatch.setattr(ingest.shutil, "which", fake_which)
    d = tempfile.mkdtemp()
    ingest.cleanup(d)
    assert called["which"] is False  # short-circuited before the docker branch


def test_cleanup_reclaims_root_owned_leftovers(monkeypatch, tmp_path):
    # Simulate rmtree failing to remove root-owned files: the cleanup must fall back
    # to a root Docker container that chowns the tree, then retry.
    leftover = tmp_path / "ws"
    leftover.mkdir()
    monkeypatch.setattr(ingest.shutil, "rmtree", lambda *a, **k: None)  # never deletes
    monkeypatch.setattr(ingest.shutil, "which", lambda _: "/usr/bin/docker")

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr(ingest.subprocess, "run", fake_run)
    ingest.cleanup(str(leftover))

    assert captured["cmd"][:3] == ["docker", "run", "--rm"]
    assert "chown" in captured["cmd"]
    assert "/target" in captured["cmd"]
