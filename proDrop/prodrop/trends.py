"""Transparent scoring for candidate dropshipping products.

Pure Python (no Frappe imports) so it can be tested without a bench.
The weights are a starting heuristic: tune them against your real sales data.
"""

from dataclasses import dataclass

WEIGHTS = {"demand": 0.40, "margin": 0.35, "competition": 0.25}
FULL_MARGIN_PCT = 60.0  # a margin at or above this earns the full margin score


@dataclass(frozen=True)
class Candidate:
	name: str
	demand: float  # 0-100: normalised search / ad / sales momentum
	cost: float  # landed supplier cost
	price: float  # planned selling price
	competition: float  # 0-100: higher means a more crowded market


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
	return max(low, min(high, value))


def margin_pct(cost: float, price: float) -> float:
	if price <= 0:
		return 0.0
	return max(0.0, (price - cost) / price * 100)


def score(candidate: Candidate) -> float:
	margin_score = min(margin_pct(candidate.cost, candidate.price), FULL_MARGIN_PCT) / FULL_MARGIN_PCT * 100
	total = (
		WEIGHTS["demand"] * _clamp(candidate.demand)
		+ WEIGHTS["margin"] * margin_score
		+ WEIGHTS["competition"] * (100 - _clamp(candidate.competition))
	)
	return round(total, 1)


def rank(candidates: list[Candidate], min_margin: float = 25.0) -> list[tuple[Candidate, float]]:
	"""Drop thin-margin products, then sort best-first."""
	kept = [c for c in candidates if margin_pct(c.cost, c.price) >= min_margin]
	return sorted(((c, score(c)) for c in kept), key=lambda pair: pair[1], reverse=True)
