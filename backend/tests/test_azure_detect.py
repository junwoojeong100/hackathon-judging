from app.services.azure_detect import detect_azure


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
