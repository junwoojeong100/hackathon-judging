from app.services.executor import (
    ExecutionReport,
    _detect_stack,
    _parse_tests,
    _score,
)


def test_detect_stack_node(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert _detect_stack(str(tmp_path)) == "node"


def test_detect_stack_python(tmp_path):
    (tmp_path / "requirements.txt").write_text("")
    assert _detect_stack(str(tmp_path)) == "python"


def test_detect_stack_none(tmp_path):
    (tmp_path / "readme.md").write_text("hi")
    assert _detect_stack(str(tmp_path)) == ""


def test_detect_stack_dotnet(tmp_path):
    proj = tmp_path / "src" / "App"
    proj.mkdir(parents=True)
    (proj / "App.csproj").write_text("<Project Sdk='Microsoft.NET.Sdk' />")
    assert _detect_stack(str(tmp_path)) == "dotnet"


def test_detect_stack_java_maven(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert _detect_stack(str(tmp_path)) == "java-maven"


def test_detect_stack_java_gradle(tmp_path):
    (tmp_path / "build.gradle").write_text("plugins {}")
    assert _detect_stack(str(tmp_path)) == "java-gradle"


def test_parse_tests_dotnet():
    log = "Passed!  - Failed:     0, Passed:     5, Skipped:     0, Total:     5"
    assert _parse_tests("dotnet", log) == (5, 0)


def test_parse_tests_java_maven():
    log = "Results:\n\nTests run: 8, Failures: 1, Errors: 1, Skipped: 0"
    assert _parse_tests("java-maven", log) == (6, 2)  # 8 - 1 - 1 passed, 1+1 failed


def test_parse_tests_go():
    log = (
        "=== RUN   TestA\n--- PASS: TestA (0.00s)\n"
        "=== RUN   TestB\n--- FAIL: TestB (0.00s)\nFAIL\n"
    )
    assert _parse_tests("go", log) == (1, 1)


def test_score_build_failed():
    assert _score(ExecutionReport(build_ran=True, build_ok=False)) == 2.0


def test_score_all_tests_pass():
    r = ExecutionReport(build_ran=True, build_ok=True, test_ran=True, tests_passed=10)
    assert _score(r) == 10.0


def test_score_half_tests_pass():
    r = ExecutionReport(
        build_ran=True, build_ok=True, test_ran=True, tests_passed=1, tests_failed=1
    )
    assert _score(r) == 8.0  # 6 + 4 * 0.5


def test_score_no_build_no_test_is_none():
    assert _score(ExecutionReport()) is None


def test_parse_tests_python():
    assert _parse_tests("python", "=== 5 passed, 2 failed in 0.1s ===") == (5, 2)


def test_parse_tests_node():
    assert _parse_tests("node", "10 passing\n2 failing") == (10, 2)
