import unittest

from prodrop.suppliers.cj_freight import (
    build_tip_request,
    pick_cheapest,
    shipping_charge,
)


class TestCJFreight(unittest.TestCase):
    # LIVE API response shape: freightCalculateTip returns option and totalPostageFee.
    def test_request_matches_live_cj_payload_shape(self):
        body = build_tip_request(
            "VARIANT-1",
            50,
            "AE",
            quantity=2,
            src_country="CN",
        )

        self.assertEqual(set(body), {"reqDTOS"})
        request = body["reqDTOS"][0]
        self.assertEqual(request["srcAreaCode"], "CN")
        self.assertEqual(request["destAreaCode"], "AE")
        self.assertEqual(request["productProp"], ["ORDINARY_PRODUCT"])
        self.assertEqual(request["weight"], 50)
        self.assertEqual(
            request["freightTrialSkuList"],
            [{"vid": "VARIANT-1", "quantity": 2}],
        )
        self.assertNotIn("products", request)

    def test_zero_weight_is_rejected(self):
        with self.assertRaises(ValueError):
            build_tip_request("VARIANT-1", 0, "AE")

    def test_missing_variant_or_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            build_tip_request("", 50, "AE")
        with self.assertRaises(ValueError):
            build_tip_request("VARIANT-1", 50, "")

    def test_live_total_postage_fee_is_used(self):
        live_option = {
            "option": {"enName": "CJ Packet"},
            "totalPostageFee": "4.25",
            "discountFee": "3.90",
            "arrivalTime": "8-12",
            "quoted_at": "2026-11-25T00:00:00",
        }
        self.assertEqual(shipping_charge(live_option), 4.25)

    def test_discount_fee_is_fallback(self):
        self.assertEqual(shipping_charge({"discountFee": "3.75"}), 3.75)

    def test_error_or_missing_price_is_ignored(self):
        self.assertIsNone(shipping_charge({"error": "quote unavailable"}))
        self.assertIsNone(shipping_charge({"totalPostageFee": None}))

    def test_cheapest_live_option_is_selected(self):
        options = [
            {
                "option": {"enName": "Express"},
                "totalPostageFee": "7.10",
                "arrivalTime": "5-8",
                "quoted_at": "2026-11-25T00:00:00",
            },
            {
                "option": {"enName": "CJ Packet"},
                "totalPostageFee": "2.95",
                "arrivalTime": "10-15",
                "quoted_at": "2026-11-25T00:00:00",
            },
            {
                "option": {"enName": "Unavailable"},
                "error": "not available",
                "totalPostageFee": "0.50",
            },
        ]

        quote = pick_cheapest(options)
        self.assertIsNotNone(quote)
        self.assertEqual(quote.shipping_usd, 2.95)
        self.assertEqual(quote.method, "CJ Packet")
        self.assertEqual(quote.delivery_days, "10-15")
        self.assertEqual(quote.quoted_at, "2026-11-25T00:00:00")

    def test_no_usable_options_returns_none(self):
        self.assertIsNone(pick_cheapest([]))
        self.assertIsNone(pick_cheapest([{"error": "unavailable"}]))


if __name__ == "__main__":
    unittest.main()
