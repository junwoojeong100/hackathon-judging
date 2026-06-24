from app.services.scoring import clamp_score, compute_overall


def test_clamp_score_bounds():
    assert clamp_score(11) == 10.0
    assert clamp_score(-3) == 0.0
    assert clamp_score("not-a-number") == 0.0
    assert clamp_score(7.456) == 7.46


def test_compute_overall_weighted():
    scores = [
        {"criterion_key": "a", "score": 10},
        {"criterion_key": "b", "score": 0},
    ]
    weights = {"a": 3, "b": 1}
    # (10*3 + 0*1) / 4 = 7.5
    assert compute_overall(scores, weights) == 7.5


def test_compute_overall_ignores_unknown_keys():
    scores = [{"criterion_key": "ghost", "score": 9}]
    assert compute_overall(scores, {"a": 5}) == 0.0


def test_compute_overall_zero_weight():
    assert compute_overall([{"criterion_key": "a", "score": 5}], {"a": 0}) == 0.0
