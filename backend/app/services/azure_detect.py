"""Detect evidence that a submission is deployed to (or deployable on) Azure,
to award a configurable bonus. Looks at IaC / CI-CD / config files and known
Azure hostnames, plus an optional user-supplied live deployment URL.
"""
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

AZURE_HOST_SUFFIXES = (
    "azurewebsites.net",
    "azurecontainerapps.io",
    "azurestaticapps.net",
    "azurefd.net",
    "azureedge.net",
    "azure-api.net",
    "cloudapp.azure.com",
    "trafficmanager.net",
    "azurecr.io",
    "blob.core.windows.net",
)

# filename (lowercased) -> human signal
_SIGNAL_FILES = {
    "azure.yaml": "azd 구성(azure.yaml)",
    "azure.yml": "azd 구성(azure.yml)",
    "main.bicep": "Bicep 템플릿(main.bicep)",
    "staticwebapp.config.json": "Azure Static Web Apps 설정",
    "host.json": "Azure Functions 설정(host.json)",
}

_CONTENT_KEYWORDS = {
    "azurewebsites.net": "App Service 호스트명",
    "azurecontainerapps.io": "Container Apps 호스트명",
    "azurestaticapps.net": "Static Web Apps 호스트명",
    "azure/webapps-deploy": "GitHub Actions Azure 배포",
    "azure/login": "GitHub Actions Azure 로그인",
    "azure/static-web-apps-deploy": "GitHub Actions SWA 배포",
    "azd up": "azd 배포 명령",
    "microsoft.web/sites": "Bicep/ARM App Service 리소스",
    "microsoft.app/containerapps": "Bicep/ARM Container Apps 리소스",
    "azurecr.io": "Azure Container Registry",
}


@dataclass
class AzureEvidence:
    detected: bool = False
    has_iac: bool = False  # azd/bicep/infra/CI deploy config present
    url_live: bool = False  # provided Azure URL responded
    signals: list[str] = field(default_factory=list)


def _scan_files(root_dir: str) -> list[str]:
    signals: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        base = os.path.basename(dirpath).lower()
        if base == "infra":
            signals.append("infra/ 디렉터리(IaC)")
        for fn in filenames:
            low = fn.lower()
            if low in _SIGNAL_FILES:
                signals.append(_SIGNAL_FILES[low])
            elif low.endswith(".bicep"):
                signals.append("Bicep 템플릿")
    return signals


def _scan_content(digest_text: str) -> list[str]:
    text = digest_text.lower()
    found = []
    for kw, label in _CONTENT_KEYWORDS.items():
        if kw in text:
            found.append(label)
    return found


def _is_azure_host(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host.endswith(AZURE_HOST_SUFFIXES)


def _check_live(url: str) -> bool:
    """A genuinely deployed app answers in the 2xx/3xx range. Azure's frontend
    returns 404 for non-existent *.azurewebsites.net hosts, so 4xx/5xx are NOT live."""
    try:
        r = httpx.get(url, timeout=8.0, follow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False


def detect_azure(root_dir: str, digest_text: str, deployment_url: str = "") -> AzureEvidence:
    evidence = AzureEvidence()
    file_signals = _scan_files(root_dir)
    content_signals = _scan_content(digest_text)
    signals = file_signals + content_signals

    # IaC / CI deploy config is "strong" evidence (vs. a mere hostname mention).
    iac_content = {
        "GitHub Actions Azure 배포",
        "GitHub Actions Azure 로그인",
        "GitHub Actions SWA 배포",
        "azd 배포 명령",
        "Bicep/ARM App Service 리소스",
        "Bicep/ARM Container Apps 리소스",
    }
    evidence.has_iac = bool(file_signals) or any(s in iac_content for s in content_signals)

    if deployment_url:
        if _is_azure_host(deployment_url):
            signals.append("Azure 배포 URL 제공")
            if _check_live(deployment_url):
                evidence.url_live = True
                signals.append("배포 URL 응답 확인(live)")

    # de-duplicate while preserving order
    seen = set()
    evidence.signals = [s for s in signals if not (s in seen or seen.add(s))]
    evidence.detected = len(evidence.signals) > 0
    return evidence


def azure_bonus_points(evidence: AzureEvidence, min_pts: float, max_pts: float) -> float:
    """Graded bonus: min when Azure deployment evidence exists, max when the
    submitted Azure URL actually responds (verified live deployment). 0 if none."""
    if not evidence.detected:
        return 0.0
    return round(max_pts if evidence.url_live else min_pts, 1)
