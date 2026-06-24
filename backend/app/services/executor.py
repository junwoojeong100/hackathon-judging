"""Run an ingested project's build/test inside an isolated Docker sandbox and
produce a deterministic execution signal for scoring.

Security: untrusted code is executed only inside an ephemeral Docker container
with dropped capabilities, no-new-privileges, and CPU/memory/PID/time limits.
If Docker is unavailable the whole step degrades gracefully (available=False).
"""
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field


@dataclass
class ExecutionReport:
    available: bool = False  # was execution actually performed?
    stack: str = ""  # node | python | go | ""
    build_ran: bool = False
    build_ok: bool = False
    test_ran: bool = False
    tests_passed: int = 0
    tests_failed: int = 0
    score: float | None = None  # 0-10, or None when not applicable
    summary: str = ""
    log_excerpt: str = ""
    signals: list[str] = field(default_factory=list)


# stack -> (docker image, in-container shell script)
# NOTE: `set -o pipefail` is REQUIRED — every gated command is piped into `tail`,
# and without pipefail the pipeline's exit status would be tail's (always 0), so
# build/install/test failures would be silently scored as successes.
_NODE_SCRIPT = (
    "set -e; set -o pipefail; "
    "echo '::install'; npm install --no-audit --no-fund --silent 2>&1 | tail -n 40 || exit 31; "
    "echo '::build'; (npm run build --if-present 2>&1 | tail -n 40) || exit 32; "
    "echo '::test'; npm test 2>&1 | tail -n 120 || exit 33; "
    "echo '::done'"
)
_PY_SCRIPT = (
    "set -e; set -o pipefail; "
    "echo '::install'; "
    "if [ -f requirements.txt ]; then pip install -q -r requirements.txt 2>&1 | tail -n 40 || exit 31; fi; "
    "if [ -f pyproject.toml ] && [ ! -f requirements.txt ]; then pip install -q . 2>&1 | tail -n 40 || exit 31; fi; "
    "echo '::build'; python -c 'import compileall,sys; sys.exit(0 if compileall.compile_dir(\".\", quiet=1) else 1)' || exit 32; "
    "echo '::test'; (python -m pytest -q 2>&1 | tail -n 120) || exit 33; "
    "echo '::done'"
)
_GO_SCRIPT = (
    "set -e; set -o pipefail; "
    "echo '::build'; go build ./... 2>&1 | tail -n 40 || exit 32; "
    "echo '::test'; go test -v ./... 2>&1 | tail -n 200 || exit 33; "
    "echo '::done'"
)
_DOTNET_SCRIPT = (
    "set -e; set -o pipefail; "
    "echo '::install'; dotnet restore 2>&1 | tail -n 40 || exit 31; "
    "echo '::build'; dotnet build -c Release 2>&1 | tail -n 40 || exit 32; "
    "echo '::test'; dotnet test -c Release 2>&1 | tail -n 160 || exit 33; "
    "echo '::done'"
)
_JAVA_MAVEN_SCRIPT = (
    "set -e; set -o pipefail; "
    "echo '::install'; mvn -B -q -DskipTests dependency:go-offline 2>&1 | tail -n 40 || exit 31; "
    "echo '::build'; mvn -B -q -DskipTests package 2>&1 | tail -n 40 || exit 32; "
    "echo '::test'; mvn -B test 2>&1 | tail -n 200 || exit 33; "
    "echo '::done'"
)
_JAVA_GRADLE_SCRIPT = (
    "set -e; set -o pipefail; "
    "echo '::build'; gradle --no-daemon -q build -x test 2>&1 | tail -n 40 || exit 32; "
    "echo '::test'; gradle --no-daemon test 2>&1 | tail -n 200 || exit 33; "
    "echo '::done'"
)

_IMAGES = {
    "node": ("node:20-slim", _NODE_SCRIPT),
    "python": ("python:3.12-slim", _PY_SCRIPT),
    "go": ("golang:1.22-bookworm", _GO_SCRIPT),
    "dotnet": ("mcr.microsoft.com/dotnet/sdk:8.0", _DOTNET_SCRIPT),
    "java-maven": ("maven:3.9-eclipse-temurin-21", _JAVA_MAVEN_SCRIPT),
    "java-gradle": ("gradle:8-jdk21", _JAVA_GRADLE_SCRIPT),
}


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0
    except Exception:
        return False


def _find_marker(root_dir: str, names: tuple = (), suffixes: tuple = ()) -> bool:
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in ("node_modules", ".git", "bin", "obj", "target", ".gradle", "packages")
        ]
        for f in filenames:
            low = f.lower()
            if low in names or any(low.endswith(s) for s in suffixes):
                return True
    return False


def _detect_stack(root_dir: str) -> str:
    def has(name: str) -> bool:
        return os.path.exists(os.path.join(root_dir, name))

    if has("package.json"):
        return "node"
    if has("requirements.txt") or has("pyproject.toml") or has("setup.py"):
        return "python"
    if has("go.mod"):
        return "go"
    if _find_marker(root_dir, suffixes=(".sln", ".csproj")):
        return "dotnet"
    if _find_marker(root_dir, names=("pom.xml",)):
        return "java-maven"
    if _find_marker(root_dir, names=("build.gradle", "build.gradle.kts")):
        return "java-gradle"
    return ""


def _parse_tests(stack: str, log: str) -> tuple[int, int]:
    """Best-effort pass/fail extraction from common test runners."""
    import re

    passed = failed = 0
    if stack == "python":
        m = re.search(r"(\d+) passed", log)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", log)
        if m:
            failed = int(m.group(1))
    elif stack == "dotnet":
        # "Passed!  - Failed:     0, Passed:     5, Skipped:     0, ..."
        m = re.search(r"Passed:\s*(\d+)", log)
        if m:
            passed = int(m.group(1))
        m = re.search(r"Failed:\s*(\d+)", log)
        if m:
            failed = int(m.group(1))
    elif stack == "go":
        # `go test -v` emits "--- PASS: TestX" / "--- FAIL: TestY"
        passed = len(re.findall(r"^--- PASS:", log, re.MULTILINE))
        failed = len(re.findall(r"^--- FAIL:", log, re.MULTILINE))
    elif stack.startswith("java"):
        # Maven Surefire: "Tests run: 10, Failures: 0, Errors: 0, Skipped: 1"
        best = None
        for m in re.finditer(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)", log
        ):
            run, fa, er = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if best is None or run > best[0]:
                best = (run, fa, er)
        if best:
            run, fa, er = best
            failed = fa + er
            passed = max(0, run - fa - er)
    else:
        # ava / jest / mocha / tap style
        for pat in [r"(\d+) passed", r"(\d+) passing", r"# pass (\d+)"]:
            m = re.search(pat, log)
            if m:
                passed = max(passed, int(m.group(1)))
        for pat in [r"(\d+) failed", r"(\d+) failing", r"# fail (\d+)"]:
            m = re.search(pat, log)
            if m:
                failed = max(failed, int(m.group(1)))
    return passed, failed


def _score(report: ExecutionReport) -> float | None:
    if not report.build_ran and not report.test_ran:
        return None
    if report.build_ran and not report.build_ok:
        return 2.0
    # build ok (or no build step but tests ran)
    if report.test_ran:
        total = report.tests_passed + report.tests_failed
        if total > 0:
            ratio = report.tests_passed / total
            return round(6.0 + 4.0 * ratio, 2)
        # tests ran but counts unknown -> treat exit code (already build_ok)
        return 8.0
    return 7.0  # builds but no tests detected


def run_execution(root_dir: str, timeout: int) -> ExecutionReport:
    report = ExecutionReport()

    if not docker_available():
        report.summary = "Docker를 사용할 수 없어 실행 검증을 건너뛰었습니다."
        return report

    stack = _detect_stack(root_dir)
    if not stack:
        report.available = True
        report.summary = "빌드/테스트 가능한 프로젝트 구성을 찾지 못했습니다 (실행 점수 제외)."
        return report

    image, script = _IMAGES[stack]
    report.available = True
    report.stack = stack
    name = f"hjexec_{uuid.uuid4().hex[:12]}"

    cmd = [
        "docker", "run", "--rm", "--name", name,
        "--network", "bridge",  # needed for dependency installs
        "--memory", "2g", "--cpus", "2", "--pids-limit", "256",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "-v", f"{os.path.abspath(root_dir)}:/work", "-w", "/work",
        image, "bash", "-lc", script,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        code = proc.returncode
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)
        report.build_ran = True
        report.score = 2.0
        report.summary = f"실행이 제한 시간({timeout}s)을 초과해 중단되었습니다."
        report.signals.append("timeout")
        return report
    except Exception as exc:  # noqa: BLE001
        report.summary = f"실행 샌드박스 오류로 건너뜀: {exc}"
        report.available = False
        return report

    report.log_excerpt = out[-2000:]
    report.build_ran = "::build" in out or stack == "go"
    report.test_ran = "::test" in out

    # exit codes: 31 install fail, 32 build fail, 33 test fail, 0 all ok
    if code in (0, 33):
        report.build_ok = True
    if code == 31:
        report.build_ran = True
        report.build_ok = False
        report.summary = f"[{stack}] 의존성 설치 실패"
        report.signals.append("install-failed")
    elif code == 32:
        report.build_ran = True
        report.build_ok = False
        report.summary = f"[{stack}] 빌드 실패"
        report.signals.append("build-failed")

    if report.test_ran:
        report.tests_passed, report.tests_failed = _parse_tests(stack, out)

    report.score = _score(report)

    if not report.summary:
        if code == 0:
            report.summary = (
                f"[{stack}] 빌드 성공"
                + (
                    f", 테스트 {report.tests_passed}건 통과"
                    + (f"/{report.tests_failed}건 실패" if report.tests_failed else "")
                    if report.test_ran
                    else " (테스트 없음)"
                )
            )
        elif code == 33:
            report.summary = (
                f"[{stack}] 빌드 성공, 테스트 실패 "
                f"({report.tests_passed} 통과 / {report.tests_failed} 실패)"
            )
        else:
            report.summary = f"[{stack}] 실행 종료 코드 {code}"

    return report
