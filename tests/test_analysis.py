import unittest

from prodrop.analysis import CONFIGURED, LIVE_CJ, PROADS, FreightResult, Item, Settings, run_analysis

S = Settings(fx_usd_to_aed=3.672, payment_fee_pct=3, refund_rate_pct=0,
             ad_spend_per_sale_aed=10, shipping_fallback_usd=3.0)
NOW = "2026-11-25T06:00:00Z"


def live(usd):
	return lambda vid: FreightResult(shipping_usd=usd, quoted_at="2026-11-25T05:59:00Z")


class TestAnalysis(unittest.TestCase):
	def test_healthy_product_no_recommendation(self):
		item = Item("Good", "v1", 2.0, 100, 50, 150.0)
		self.assertEqual(run_analysis([item], S, live(2.71), NOW), [])

	def test_thin_margin_recommended_with_sources(self):
		item = Item("Thin", "v1", 20.0, 100, 50, 100.0)
		recs = run_analysis([item], S, live(2.71), NOW)
		self.assertEqual(len(recs), 1)
		src = recs[0]["evidence"]["data_sources"]
		self.assertEqual(src["supplier_cost"]["source"], LIVE_CJ)
		self.assertEqual(src["shipping"]["source"], LIVE_CJ)
		self.assertEqual(src["shipping"]["retrieved_at"], "2026-11-25T05:59:00Z")
		self.assertEqual(src["ad_spend"]["source"], CONFIGURED)
		self.assertEqual(recs[0]["status"], "Pending")

	def test_failed_freight_uses_labelled_fallback(self):
		item = Item("Thin", "v1", 20.0, 100, 50, 100.0)
		recs = run_analysis([item], S, lambda vid: None, NOW)
		self.assertEqual(recs[0]["evidence"]["data_sources"]["shipping"]["source"], CONFIGURED)

	def test_proads_data_used_when_supplied(self):
		item = Item("Ads", "v1", 2.0, 100, 50, 150.0)
		recs = run_analysis([item], S, live(2.0), NOW, ad_spend_by_product={"Ads": 140.0})
		self.assertEqual(len(recs), 1)
		self.assertEqual(recs[0]["evidence"]["data_sources"]["ad_spend"]["source"], PROADS)

	def test_zero_warehouse_stock_recommended(self):
		item = Item("Stuck", "v1", 2.0, 12810, 0, 150.0)
		recs = run_analysis([item], S, live(2.0), NOW)
		self.assertEqual([r["kind"] for r in recs], ["pause_product"])
		self.assertIn("warehouse", recs[0]["signal"])

	def test_nothing_is_executed(self):
		# Output is data only: no status other than Pending, no price or stock changes.
		item = Item("Thin", "v1", 20.0, 100, 0, 100.0)
		for rec in run_analysis([item], S, live(2.71), NOW):
			self.assertEqual(rec["status"], "Pending")

	def test_unknown_warehouse_stock_skips_check(self):
		item = Item("Unknown", "v1", 2.0, None, None, 150.0)
		self.assertEqual(run_analysis([item], S, live(2.0), NOW), [])


if __name__ == "__main__":
	unittest.main()


from prodrop.analysis import drop_already_pending  # noqa: E402


class TestDedupe(unittest.TestCase):
	def test_existing_pending_skipped(self):
		recs = [{"product": "A", "kind": "pause_product"}, {"product": "B", "kind": "pause_product"}]
		self.assertEqual(drop_already_pending(recs, {("A", "pause_product")}), [recs[1]])

	def test_same_product_different_kind_kept(self):
		recs = [{"product": "A", "kind": "pricing"}]
		self.assertEqual(drop_already_pending(recs, {("A", "pause_product")}), recs)

	def test_empty_pending_keeps_all(self):
		recs = [{"product": "A", "kind": "pause_product"}]
		self.assertEqual(drop_already_pending(recs, set()), recs)
