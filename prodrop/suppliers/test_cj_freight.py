import unittest

from prodrop.suppliers.cj_freight import build_tip_request, pick_cheapest, shipping_charge

# Shaped from the live CJ response for variant 2406150633381612900 to AE
LIVE = [
	{"arrivalTime": "12-50", "discountFee": 2.71, "totalPostageFee": 2.71, "taxesFee": None,
	 "remoteFee": 0, "error": "", "option": {"enName": "CJPacket Eub"}},
	{"arrivalTime": "12-50", "discountFee": 2.82, "totalPostageFee": 2.82, "taxesFee": None,
	 "remoteFee": 0, "error": "", "option": {"enName": "CJPacket Eub Special Line"}},
	{"arrivalTime": "10-20", "discountFee": None, "totalPostageFee": None, "error": "",
	 "option": {"enName": "Unpriced line"}},
	{"arrivalTime": "5-10", "discountFee": 0.90, "totalPostageFee": 0.90, "error": "not available",
	 "option": {"enName": "Errored line"}},
]


class TestFreight(unittest.TestCase):
	def test_request_matches_live_shape(self):
		item = build_tip_request("V1", 50, "AE")["reqDTOS"][0]
		self.assertEqual(item["productProp"], ["ORDINARY_PRODUCT"])
		self.assertEqual(item["freightTrialSkuList"], [{"vid": "V1", "quantity": 1}])
		self.assertNotIn("products", item)

	def test_zero_weight_and_missing_destination_rejected(self):
		with self.assertRaises(ValueError):
			build_tip_request("V1", 0, "AE")
		with self.assertRaises(ValueError):
			build_tip_request("V1", 50, "")

	def test_charge_prefers_total_postage(self):
		self.assertEqual(shipping_charge(LIVE[0]), 2.71)
		self.assertEqual(shipping_charge({"discountFee": 3.0, "totalPostageFee": None, "error": ""}), 3.0)

	def test_errored_and_unpriced_skipped(self):
		self.assertIsNone(shipping_charge(LIVE[3]))

	def test_cheapest_from_live_response(self):
		q = pick_cheapest(LIVE)
		self.assertEqual(q.shipping_usd, 2.71)
		self.assertEqual(q.method, "CJPacket Eub")

	def test_no_usable_options(self):
		self.assertIsNone(pick_cheapest([]))


if __name__ == "__main__":
	unittest.main()
