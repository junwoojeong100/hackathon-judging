from app.services.azure_detect import (
    AzureEvidence,
    _is_azure_host,
    azure_bonus_points,
    detect_azure,
)


def test_is_azure_host_requires_dot_boundary():
    assert _is_azure_host("https://app.azurewebsites.net") is True
    assert _is_azure_host("https://azurewebsites.net") is True
    assert _is_azure_host("https://myazurewebsites.net") is False  # spoof attempt
    assert _is_azure_host("https://evil.com") is False


def test_azure_bonus_none_when_not_detected():
    assert azure_bonus_points(AzureEvidence(detected=False), 20, 30) == 0.0


def test_azure_bonus_detected_not_live_is_min():
    ev = AzureEvidence(detected=True, has_iac=True, url_live=False)
    assert azure_bonus_points(ev, 20, 30) == 20.0


def test_azure_bonus_live_is_max():
    ev = AzureEvidence(detected=True, has_iac=False, url_live=True)
    assert azure_bonus_points(ev, 20, 30) == 30.0


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
