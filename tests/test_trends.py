import unittest

from prodrop.trends import Candidate, margin_pct, rank, score


class TestTrends(unittest.TestCase):
	def test_margin(self):
		self.assertEqual(margin_pct(10, 40), 75.0)
		self.assertEqual(margin_pct(50, 40), 0.0)
		self.assertEqual(margin_pct(10, 0), 0.0)

	def test_score_bounds(self):
		best = Candidate("a", demand=150, cost=1, price=100, competition=-5)
		worst = Candidate("b", demand=-10, cost=100, price=100, competition=200)
		self.assertEqual(score(best), 100.0)
		self.assertEqual(score(worst), 0.0)

	def test_rank_filters_and_orders(self):
		good = Candidate("good", 80, 10, 40, 20)
		okay = Candidate("okay", 50, 20, 40, 50)
		thin = Candidate("thin", 99, 38, 40, 10)
		ranked = rank([okay, thin, good])
		self.assertEqual([c.name for c, _ in ranked], ["good", "okay"])


if __name__ == "__main__":
	unittest.main()
