import unittest

from prodrop.profit import Economics, assess_product, assess_warehouse_stock, cash_hold


def econ(**kw):
	base = dict(selling_price=100, supplier_cost=30, shipping=10, payment_fee_pct=3,
	            refund_rate_pct=0, ad_spend_per_sale=10)
	base.update(kw)
	return Economics(**base)


class TestProfit(unittest.TestCase):
	def test_net_profit_no_refunds(self):
		# 100 - 30 - 10 - 10 - 3 = 47
		self.assertEqual(econ().expected_net_profit(), 47.0)

	def test_refunds_reduce_profit(self):
		self.assertLess(econ(refund_rate_pct=20).expected_net_profit(), econ().expected_net_profit())

	def test_thin_margin_is_flagged(self):
		rec = assess_product("thin", econ(supplier_cost=75))
		self.assertIsNotNone(rec)
		self.assertEqual(rec.kind, "pause_product")
		self.assertEqual(rec.status, "Pending")

	def test_healthy_margin_not_flagged(self):
		self.assertIsNone(assess_product("good", econ()))

	def test_zero_price_safe(self):
		self.assertEqual(econ(selling_price=0).net_margin_pct(), 0.0)

	def test_warehouse_zero_flagged(self):
		self.assertIsNotNone(assess_warehouse_stock("v1", 12810, 0))
		self.assertIsNone(assess_warehouse_stock("v1", 12810, 5))

	def test_cash_hold(self):
		self.assertIsNotNone(cash_hold(100, 80, 30, 10))
		self.assertIsNone(cash_hold(500, 80, 30, 10))

	def test_recommendation_is_record_ready(self):
		rec = cash_hold(0, 50, 0, 0)
		self.assertEqual(rec.as_dict()["status"], "Pending")


if __name__ == "__main__":
	unittest.main()
