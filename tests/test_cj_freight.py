import unittest

from prodrop.suppliers.cj_freight import build_tip_request, pick_cheapest


class TestFreight(unittest.TestCase):
	def test_request_shape(self):
		body = build_tip_request("V1", 50, "AE")
		item = body["reqDTOS"][0]
		self.assertEqual(item["destAreaCode"], "AE")
		self.assertEqual(item["weight"], 50)
		self.assertEqual(item["products"], [{"vid": "V1", "quantity": 1}])

	def test_zero_weight_rejected(self):
		with self.assertRaises(ValueError):
			build_tip_request("V1", 0, "AE")

	def test_missing_destination_rejected(self):
		with self.assertRaises(ValueError):
			build_tip_request("V1", 50, "")

	def test_cheapest_option_chosen(self):
		q = pick_cheapest([
			{"logisticName": "A", "price": "4.10", "logisticAging": "10-15"},
			{"logisticName": "B", "price": "2.95", "logisticAging": "15-25"},
		])
		self.assertEqual(q.shipping_usd, 2.95)
		self.assertEqual(q.method, "B")

	def test_unpriced_options_skipped(self):
		q = pick_cheapest([{"logisticName": "X", "price": None}, {"logisticName": "Y", "price": "3.00"}])
		self.assertEqual(q.method, "Y")

	def test_no_options_returns_none(self):
		self.assertIsNone(pick_cheapest([]))


if __name__ == "__main__":
	unittest.main()
