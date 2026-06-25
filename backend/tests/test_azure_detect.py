from unittest.mock import patch

from app.services import azure_detect
from app.services.azure_detect import (
    AzureEvidence,
    _is_azure_host,
    azure_points,
    detect_azure,
)


def test_is_azure_host_requires_dot_boundary():
    assert _is_azure_host("https://app.azurewebsites.net") is True
    assert _is_azure_host("https://azurewebsites.net") is True
    assert _is_azure_host("https://myazurewebsites.net") is False  # spoof attempt
    assert _is_azure_host("https://evil.com") is False


def test_azure_points_zero_when_not_detected():
    assert azure_points(AzureEvidence(detected=False), 20) == 0.0


def test_azure_points_full_when_detected():
    ev = AzureEvidence(detected=True, has_iac=True, url_live=False)
    assert azure_points(ev, 20) == 20.0
    live = AzureEvidence(detected=True, has_iac=False, url_live=True)
    assert azure_points(live, 20) == 20.0


def test_detect_azure_bicep_file(tmp_path):
    (tmp_path / "main.bicep").write_text("resource s 'Microsoft.Web/sites' = {}")
    ev = detect_azure(str(tmp_path), "", "")
    assert ev.detected is True
    assert any("Bicep" in s for s in ev.signals)


def test_detect_azure_from_content(tmp_path):
    ev = detect_azure(str(tmp_path), "배포 주소: https://app.azurewebsites.net", "")
    assert ev.detected is True


def test_detect_azure_none(tmp_path):
    (tmp_path / "readme.md").write_text("just a plain project")
    ev = detect_azure(str(tmp_path), "console.log('hi')", "")
    assert ev.detected is False
    assert ev.signals == []


def test_detect_azure_infra_dir(tmp_path):
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "deploy.bicep").write_text("// bicep")
    ev = detect_azure(str(tmp_path), "", "")
    assert ev.detected is True


def test_detect_azure_github_actions_workflow(tmp_path):
    # `.github/workflows/*` is pruned from the digest, so a CI-only Azure deploy
    # must be detected by scanning the workflow files directly.
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "deploy.yml").write_text(
        "jobs:\n  build:\n    steps:\n"
        "      - uses: azure/login@v2\n      - uses: azure/webapps-deploy@v3\n"
    )
    ev = detect_azure(str(tmp_path), "", "")  # empty digest on purpose
    assert ev.detected is True
    assert azure_points(ev, 20) == 20.0
    assert ev.has_iac is True


def test_nonlive_url_alone_does_not_score(tmp_path):
    # A plausible but unreachable *.azurewebsites.net URL must not, on its own,
    # grant the required-criterion points (anti-gaming).
    with patch.object(azure_detect, "_check_live", return_value=False):
        ev = detect_azure(str(tmp_path), "", "https://made-up-xyz.azurewebsites.net")
    assert ev.detected is False
    assert ev.url_live is False
    assert azure_points(ev, 20) == 0.0


def test_live_url_alone_scores(tmp_path):
    with patch.object(azure_detect, "_check_live", return_value=True):
        ev = detect_azure(str(tmp_path), "", "https://real-app.azurewebsites.net")
    assert ev.detected is True
    assert ev.url_live is True
    assert azure_points(ev, 20) == 20.0

