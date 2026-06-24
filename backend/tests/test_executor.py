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
