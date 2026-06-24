"""Weighted score aggregation helpers."""


def clamp_score(value, lo: float = 0.0, hi: float = 10.0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(lo, min(hi, v)), 2)


def compute_overall(scores: list[dict], weights: dict[str, int]) -> float:
    """scores: [{"criterion_key": str, "score": float}] -> 0-10 weighted average."""
    total_weight = 0
    acc = 0.0
    for s in scores:
        w = weights.get(s["criterion_key"], 0)
        acc += float(s["score"]) * w
        total_weight += w
    if total_weight == 0:
        return 0.0
    return round(acc / total_weight, 2)


def compute_absolute(scores: list[dict], weights: dict[str, int]) -> float:
    """Absolute points: each criterion contributes (score/10) * weight, where the
    weight is its point cap. Returns the summed points (0 .. sum of weights)."""
    return round(
        sum((float(s["score"]) / 10.0) * weights.get(s["criterion_key"], 0) for s in scores),
        1,
    )
